#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "6502-emu_wrapper.h"
#include "libcrabapple.h"
#include "libdebugger.h"
#include "libudis.h"

uint16_t cycles_per_scan_line;
uint32_t cycles_per_frame;
int extra_cycles_in_previous_frame;
uint32_t frame_number;
op_history_t *current_op_history;
op_history_t *current_input_history;
int apple2_mode = 0;


uint8_t simple_kernel[] = {
	0xa9,0x00,0x85,0x80,0xa9,0x20,0x85,0x81,
	0xa9,0x40,0x85,0x82,0xa9,0x00,0x85,0x83,
	0xa5,0x81,0x85,0x84,0xa0,0x00,0xa5,0x80,
	0x91,0x83,0xc8,0xd0,0xfb,0xe6,0x84,0xa6,
	0x84,0xe4,0x82,0x90,0xf3,0xe6,0x80,0x18,
	0x90,0xe2};

void lib6502_init_debug_kernel() {
	int i;

	for (i=0; i<sizeof(simple_kernel); i++) {
		memory[0xf000 + i] = simple_kernel[i];
	}
	PC = 0xf000;
}

void lib6502_init_cpu(int scan_lines, int cycles_per) {
	init_tables();

	A = 0;
	X = 0;
	Y = 0;
	SP = 0xff;
	SR.byte = 0;
	PC = 0xfffe;
	memset(memory, 0, sizeof(memory));

	cycles_per_scan_line = cycles_per;
	cycles_per_frame = (long)(scan_lines * cycles_per_scan_line);
	extra_cycles_in_previous_frame = 0;

	// create instruction history with plenty of extra space. Since
	// instructions are at least 2 cycles, there should be way fewer than
	// cycles_per_frame instructions in a frame. And, for the number of delta
	// entries, this assumes there won't be more than 10 deltas for every
	// instruction
	current_op_history = create_op_history(10 * cycles_per_frame, cycles_per_frame);
	print_op_history(current_op_history);
	
	// create input history with plenty of extra space; assuming that there
	// won't be more than one input per CPU cycle
	current_input_history = create_op_history(cycles_per_frame, cycles_per_frame);

	frame_number = 0;

	liba2_init_graphics();

	lib6502_init_debug_kernel();
}

int lib6502_cold_start(op_history_t *input)
{
	//load memory, configure emulator state, etc. to produce frame 0
	frame_number = 0;
	return 0;
}

emulator_state_t *lib6502_export_frame() {
	emulator_state_t *buf;
	lib6502_emulator_state_t *state;
	int video_size, audio_size;

	if (apple2_mode) {
		video_size = sizeof(a2_video_output_t);
	}
	else {
		video_size = 0;
	}
	audio_size = 0;
	buf = create_emulator_state(sizeof(lib6502_emulator_state_t), 0, video_size, audio_size);
	buf->frame_number = frame_number;
	buf->emulator_id = LIB6502_EMULATOR_ID;

	state = (lib6502_emulator_state_t *)SAVE_STATE_PTR(buf);
	state->cycles_per_scan_line = cycles_per_scan_line;
	state->cycles_per_frame = cycles_per_frame;
	state->apple2_mode = apple2_mode;
	state->extra_cycles_in_previous_frame = extra_cycles_in_previous_frame;
	save16(state->PC, PC);
	state->A = A;
	state->X = X;
	state->Y = Y;
	state->SP = SP;
	state->SR = SR.byte;
	memcpy(state->memory, memory, 1<<16);
	if (apple2_mode) liba2_export_state(buf);
	return buf;
}

void lib6502_import_frame(emulator_state_t *buf) {
	lib6502_emulator_state_t *state;

	frame_number = buf->frame_number;
	state = (lib6502_emulator_state_t *)SAVE_STATE_PTR(buf);
	cycles_per_scan_line = state->cycles_per_scan_line;
	cycles_per_frame = state->cycles_per_frame;
	apple2_mode = state->apple2_mode;
	extra_cycles_in_previous_frame = state->extra_cycles_in_previous_frame;
	A = state->A;
	X = state->X;
	Y = state->Y;
	SP = state->SP;
	load16(PC, state->PC);
	SR.byte = state->SR;
	memcpy(memory, state->memory, 1<<16);
	if (apple2_mode) liba2_import_state(buf);
}

void lib6502_fill_current_state(current_state_t *buf) {
	buf->frame_number = frame_number;
	buf->pc = PC;
	buf->reg_byte[REG_A] = A;
	buf->reg_byte[REG_X] = X;
	buf->reg_byte[REG_Y] = Y;
	buf->reg_byte[REG_SP] = SP;
	buf->reg_byte[REG_SR] = SR.byte;
	memcpy(buf->memory, memory, 1<<16);
}

int lib6502_step_cpu()
{
	int count, bpid;
	uint8_t last_sp, last_sr, opcode, cycles;
	char flag;
	intptr_t index;
	uint16_t line, addr;
	history_breakpoint_t *b;

	last_sp = SP;
	last_sr = SR.byte;

	opcode = memory[PC];
	inst = instructions[opcode];
	count = lengths[inst.mode];
	flag = opcode_history_flags_6502[opcode];
 
	op_history_add_instruction(current_op_history, PC, &memory[PC], count);
	op_history_one_byte_reg(current_op_history, EMU_COLOR_CLOCK, tv_cycle);
	op_history_two_byte_reg(current_op_history, EMU_SCAN_LINE, tv_line);

	write_addr = NULL;
	read_addr = NULL;
	result_flag = NOP;
	opcode_ref_addr = -1;
	extra_cycles = 0;
	before_value_index = 0;

	inst.function();
	if (result_flag == JUMP || result_flag == BRANCH_TAKEN) {
		op_history_new_pc(current_op_history, PC);
	}
	else {
		PC += count;
	}

	// record if the opcode references an address (e.g. LDA $8000, LDA $8000,X,
	// STA ($80),X, etc.
	if (opcode_ref_addr >= 0) {
		op_history_opcode_ref_addr(current_op_history, opcode_ref_addr);
	}

	// // record actual address of a read or write, including any indexing
	// // operation in the address, so if X = FF and the opcode is LDA $8000,X,
	// // the address recorded here will be $80FF
	// if (read_addr >= 0) {
	// 	op_history_computed_addr(current_op_history, (uint8_t *)read_addr - memory);
	// }
	// else if (write_addr >= 0) {
	// 	op_history_computed_addr(current_op_history, (uint8_t *)read_addr - memory);
	// }

	// 7 cycle instructions (e.g. ROL $nnnn,X) don't have a penalty cycle for
	// crossing a page boundary.
	if (inst.cycles == 7) extra_cycles = 0;
	cycles = inst.cycles + extra_cycles;

	if (apple2_mode) liba2_copy_video(cycles);

	if (result_flag == BRANCH_TAKEN) {
		op_history_branch_taken(current_op_history);
	}
	else if (result_flag == BRANCH_NOT_TAKEN) {
		op_history_branch_not_taken(current_op_history);
	}
	
	if (flag == FLAG_PEEK_MEMORY || flag == FLAG_LOAD_A_FROM_MEMORY || flag == FLAG_LOAD_X_FROM_MEMORY || flag == FLAG_LOAD_Y_FROM_MEMORY) {
		addr = (uint8_t *)read_addr - memory;
		op_history_computed_address(current_op_history, addr);
		op_history_read_address(current_op_history, addr, *(uint8_t *)read_addr);
		if (apple2_mode) {
			liba2_read_softswitch(addr);
		}
	}
	else if (flag == FLAG_STORE_A_IN_MEMORY || flag == FLAG_STORE_X_IN_MEMORY || flag == FLAG_STORE_Y_IN_MEMORY || flag == FLAG_MEMORY_ALTER) {
		addr = (uint8_t *)write_addr - memory;
		op_history_computed_address(current_op_history, addr);
		op_history_write_address(current_op_history, addr, *(uint8_t *)write_addr);
		if (apple2_mode) {
			liba2_write_softswitch(addr);
		}
	}
	
	if (flag == FLAG_REG_A || flag == FLAG_LOAD_A_FROM_MEMORY) {
		op_history_one_byte_reg(current_op_history, REG_A, A);
	}
	else if (flag == FLAG_REG_X || flag == FLAG_LOAD_X_FROM_MEMORY) {
		op_history_one_byte_reg(current_op_history, REG_X, X);
	}
	else if (flag == FLAG_REG_Y || flag == FLAG_LOAD_Y_FROM_MEMORY) {
		op_history_one_byte_reg(current_op_history, REG_Y, Y);
	}

	/* Maximum of 3 bytes will have changed on the stack */
	if (last_sp < SP) {
		last_sp++;
		op_history_read_address(current_op_history, 0x100 + last_sp, memory[last_sp]);
		if (last_sp < SP) {
			last_sp++;
			op_history_read_address(current_op_history, 0x100 + last_sp, memory[last_sp]);
		}
		if (last_sp < SP) {
			last_sp++;
			op_history_read_address(current_op_history, 0x100 + last_sp, memory[last_sp]);
		}
		op_history_one_byte_reg(current_op_history, REG_SP, last_sp);
	}
	else if (last_sp > SP) {
		op_history_write_address(current_op_history, 0x100 + last_sp, memory[last_sp]);
		last_sp--;
		if (last_sp > SP) {
			op_history_write_address(current_op_history, 0x100 + last_sp, memory[last_sp]);
			last_sp--;
		}
		if (last_sp > SP) {
			op_history_write_address(current_op_history, 0x100 + last_sp, memory[last_sp]);
			last_sp--;
		}
		op_history_one_byte_reg(current_op_history, REG_SP, last_sp);
	}

	if (last_sr != SR.byte) {
		op_history_one_byte_reg(current_op_history, REG_SR, SR.byte);
	}

	return cycles;
}

int lib6502_next_frame(op_history_t *input)
{
	int cycle_count, cycles;

	if (apple2_mode) {
		// if (input->keychar > 0) {
		// 	printf("lib6502_next_frame: apple2_mode key = %x\n", input->keychar);
		// }
		// memory[0xc000] = input->keychar;
	}

	frame_number++;
	clear_op_history(current_op_history);

	op_history_start_frame(current_op_history, PC, frame_number);
	print_op_history(current_op_history);

	// start cycle count after skipping any cycles that were processed last
	// frame but where the instruction crossed over into this frame
	cycle_count = extra_cycles_in_previous_frame;
	tv_cycle = cycle_count;
	tv_line = 0;
	
	while (cycle_count < cycles_per_frame) {
		cycles = lib6502_step_cpu();
		cycle_count += cycles;
		tv_cycle += cycles;
		if (tv_cycle > cycles_per_scan_line) {
			tv_cycle -= cycles_per_scan_line;
			tv_line++;
		}
	}

	op_history_end_frame(current_op_history, PC);
	return frame_number;
}

op_history_t *lib6502_copy_op_history() {
	return copy_op_history(current_op_history);
}

void lib6502_set_a2_emulation_mode(int mode) {
	if (mode) apple2_mode = 1;
	else apple2_mode = 0;
}
