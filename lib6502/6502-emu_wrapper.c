#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "6502-emu_wrapper.h"
#include "libdebugger.h"
#include "libudis.h"

long cycles_per_frame;

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

void lib6502_init_cpu(float frequency_mhz, float refresh_rate_hz) {
	init_tables();

	A = 0;
	X = 0;
	Y = 0;
	SP = 0xff;
	SR.byte = 0;
	PC = 0xfffe;
	memset(memory, 0, sizeof(memory));

	cycles_per_frame = (long)((frequency_mhz * 1000000.0) / refresh_rate_hz);

	lib6502_init_debug_kernel();
}

void lib6502_clear_state_arrays(void *input, output_t *output) {
	frame_status_t *status = &output->status;

	status->frame_status = 0;
	status->cycles_since_power_on = 0;
	status->instructions_since_power_on = 0;
	status->use_memory_access = 1;
	status->brk_into_debugger = 1;
}

void lib6502_configure_state_arrays(void *input, output_t *output) {
}

void lib6502_get_current_state(output_t *buf) {
	buf->A = A;
	buf->X = X;
	buf->Y = Y;
	buf->SP = SP;
	save16(buf->PC, PC);
	buf->SR = SR.byte;
	memcpy(buf->memory, memory, 1<<16);
}

void lib6502_restore_state(output_t *buf) {
	A = buf->A;
	X = buf->X;
	Y = buf->Y;
	SP = buf->SP;
	load16(PC, buf->PC);
	SR.byte = buf->SR;
	memcpy(memory, buf->memory, 1<<16);
}

uint16_t last_pc;

int lib6502_show_current_instruction(history_6502_t *entry)
{
	int count;
	uint8_t opcode;

	opcode = memory[PC];
	count = instruction_length_6502[opcode];
	entry->pc = PC;
	entry->num_bytes = count;
	entry->flag = opcode_history_flags_6502[opcode];
	entry->instruction[0] = opcode;
	if (count > 1) entry->instruction[1] = memory[PC + 1];
	if (count > 2) entry->instruction[2] = memory[PC + 2];
	entry->a = A;
	entry->x = X;
	entry->y = Y;
	entry->sp = SP;
	entry->sr = SR.byte;
	entry->before1 = 0;
	entry->after1 = 0;
	entry->before2 = 0;
	entry->after2 = 0;
	entry->before3 = 0;
	entry->after3 = 0;
}

int lib6502_step_cpu(frame_status_t *status, history_6502_t *entry, breakpoints_t *breakpoints)
{
	int count, bpid;
	uint8_t last_sp, opcode;
	intptr_t index;
	history_breakpoint_t *b;

	last_pc = PC;
	last_sp = SP;

	opcode = memory[PC];
	inst = instructions[opcode];
	count = lengths[inst.mode];
	if (entry) lib6502_show_current_instruction(entry);

	bpid = libdebugger_check_breakpoints(breakpoints, status, &lib6502_register_callback, opcode == 0x4c);
	if (bpid >= 0) {
		status->frame_status = FRAME_BREAKPOINT;
		status->breakpoint_id = bpid;
		if (entry) {
			b = (history_breakpoint_t *)entry;
			b->breakpoint_id = bpid;
			b->breakpoint_type = breakpoints->breakpoint_type[bpid];
			b->disassembler_type = DISASM_NEXT_INSTRUCTION;
			b->disassembler_type_cpu = DISASM_6502_HISTORY;
		}
		return bpid;
	}

	write_addr = NULL;
	read_addr = NULL;
	result_flag = NOP;
	extra_cycles = 0;
	before_value_index = 0;

	if (status->use_memory_access) {
		status->memory_access[PC] = 255;
		status->access_type[PC] = ACCESS_TYPE_EXECUTE;
		if (count > 1) {
			status->memory_access[PC + 1] = 255;
			status->access_type[PC + 1] = ACCESS_TYPE_EXECUTE;
		}
		if (count > 2) {
			status->memory_access[PC + 2] = 255;
			status->access_type[PC + 2] = ACCESS_TYPE_EXECUTE;
		}
	}

	breakpoints->last_pc = PC;
	inst.function();
	if (SR.bits.brk && status->brk_into_debugger) {
		/* automatically jump into debugger on BRK */
		PC = breakpoints->last_pc;
		bpid = libdebugger_brk_instruction(breakpoints);
		status->frame_status = FRAME_BREAKPOINT;
		status->breakpoint_id = bpid;
		if (entry) {
			b = (history_breakpoint_t *)entry;
			b->breakpoint_id = bpid;
			b->breakpoint_type = breakpoints->breakpoint_type[bpid];
			b->disassembler_type = DISASM_NEXT_INSTRUCTION;
			b->disassembler_type_cpu = DISASM_6502_HISTORY;
		}
		return bpid;
	}
	if (result_flag != JUMP) PC += count;

	// 7 cycle instructions (e.g. ROL $nnnn,X) don't have a penalty cycle for
	// crossing a page boundary.
	if (inst.cycles == 7) extra_cycles = 0;
	if (entry) {
		entry->cycles = inst.cycles + extra_cycles;
		if (result_flag == BRANCH_TAKEN) {
			entry->flag = FLAG_BRANCH_TAKEN;
		}
		else if (result_flag == BRANCH_NOT_TAKEN) {
			entry->flag = FLAG_BRANCH_NOT_TAKEN;
		}
		else if (entry->flag == FLAG_PEEK_MEMORY) {
			entry->target_addr = (uint8_t *)read_addr - memory;
			entry->before1 = *(uint8_t *)read_addr;
		}
		else if (entry->flag == FLAG_STORE_A_IN_MEMORY || entry->flag == FLAG_STORE_X_IN_MEMORY || entry->flag == FLAG_STORE_Y_IN_MEMORY) {
			entry->target_addr = (uint8_t *)write_addr - memory;
			entry->before1 = before_value[0];
		}
		else if (entry->flag == FLAG_MEMORY_ALTER) {
			entry->target_addr = (uint8_t *)write_addr - memory;
			entry->before1 = before_value[0];
			entry->after1 = *(uint8_t *)write_addr;
		}
		else if (entry->a != A || entry->flag == FLAG_REG_A || entry->flag == FLAG_LOAD_A_FROM_MEMORY) {
			if (entry->flag != 0) entry->flag = FLAG_REG_A;
			entry->after1 = A;
		}
		else if (entry->x != X || entry->flag == FLAG_REG_X || entry->flag == FLAG_LOAD_X_FROM_MEMORY) {
			if (entry->flag != 0) entry->flag = FLAG_REG_X;
			entry->after1 = X;
		}
		else if (entry->y != Y || entry->flag == FLAG_REG_Y || entry->flag == FLAG_LOAD_Y_FROM_MEMORY) {
			if (entry->flag != 0) entry->flag = FLAG_REG_Y;
			entry->after1 = Y;
		}
		else if (entry->sp != SP) {
			;
		}
		else if ((before_value_index > 0) && (write_addr >= memory) && (write_addr < memory + (256*256))) {
			/* if write_addr outside of memory, the dest is a register */
			entry->target_addr = (uint8_t *)write_addr - memory;
			entry->after3 = before_value[0];
			entry->after1 = *(uint8_t *)write_addr;
			// entry->flag = FLAG_WRITE_ONE;
		}
		else if (write_addr && (write_addr >= memory) && (write_addr < memory + (256*256))) {
			entry->target_addr = (uint8_t *)write_addr - memory;
		}
		else if (read_addr && (read_addr >= memory) && (read_addr < memory + (256*256))) {
			entry->target_addr = (uint8_t *)read_addr - memory;
			// entry->flag = FLAG_READ_ONE;
		}
		if (entry->sr != SR.byte) {
			entry->flag |= FLAG_REG_SR;
			entry->after3 = SR.byte;
		}
	}

	if (status->use_memory_access) {
		if (read_addr != NULL) {
			index = (intptr_t)read_addr - (intptr_t)(&memory[0]);
			if (index >= 0 && index < MAIN_MEMORY_SIZE) {
				status->memory_access[(uint16_t)index] = 255;
				status->access_type[(uint16_t)index] = ACCESS_TYPE_READ;
			}
		}
		if (write_addr != NULL) {
			index = (intptr_t)write_addr - (intptr_t)(&memory[0]);
			if (index >= 0 && index < MAIN_MEMORY_SIZE) {
				status->memory_access[(uint16_t)index] = 255;
				status->access_type[(uint16_t)index] = ACCESS_TYPE_WRITE;
			}
		}

		/* Maximum of 3 bytes will have changed on the stack */
		if (last_sp < SP) {
			last_sp++;
			status->memory_access[0x100 + last_sp] = 255;
			status->access_type[0x100 + last_sp] = ACCESS_TYPE_READ;
			if (last_sp < SP) {
				last_sp++;
				status->memory_access[0x100 + last_sp] = 255;
				status->access_type[0x100 + last_sp] = ACCESS_TYPE_READ;
			}
			if (last_sp < SP) {
				last_sp++;
				status->memory_access[0x100 + last_sp] = 255;
				status->access_type[0x100 + last_sp] = ACCESS_TYPE_READ;
			}
		}
		else if (last_sp > SP) {
			status->memory_access[0x100 + last_sp] = 255;
			status->access_type[0x100 + last_sp] = ACCESS_TYPE_WRITE;
			last_sp--;
			if (last_sp > SP) {
				status->memory_access[0x100 + last_sp] = 255;
				status->access_type[0x100 + last_sp] = ACCESS_TYPE_WRITE;
				last_sp--;
			}
			if (last_sp > SP) {
				status->memory_access[0x100 + last_sp] = 255;
				status->access_type[0x100 + last_sp] = ACCESS_TYPE_WRITE;
				last_sp--;
			}
		}
	}

	status->current_instruction_in_frame += 1;
	status->instructions_since_power_on += 1;
	status->current_cycle_in_frame += inst.cycles + extra_cycles;
	status->cycles_since_power_on += inst.cycles + extra_cycles;
	return -1;
}

int lib6502_register_callback(uint16_t token, uint16_t addr) {
	int value;
	uint8_t opcode;

	switch (token) {
		case REG_A:
		value = A;
		break;

		case REG_X:
		value = X;
		break;

		case REG_Y:
		value = Y;
		break;

		case REG_PC:
		value = PC;
		break;

		case REG_SP:
		value = SP;
		break;

		case OPCODE_TYPE:
		opcode = memory[last_pc];
		if (opcode == 0x60) value = 8;
		else value = 0;
#ifdef DEBUG_REGISTER_CALLBACK
		printf("opcode_type at PC=%04x: opcode=%02x value=%02x\n", last_pc, opcode, value);
#endif
		break;

		default:
		value = 0;
	}
#ifdef DEBUG_REGISTER_CALLBACK
	printf("lib6502_register_callback: token=%d addr=%04x value=%04x\n", token, addr, value);
#endif
	return value;
}

int lib6502_calc_frame(frame_status_t *status, breakpoints_t *breakpoints, emulator_history_t *history)
{
	int cycles, bpid, count;
	history_6502_t *entry;
	history_frame_t *frame_entry;

	do {
		last_pc = PC;
		entry = (history_6502_t *)libudis_get_next_entry(history, DISASM_6502_HISTORY);
		status->breakpoint_id = -1;
		bpid = lib6502_step_cpu(status, entry, breakpoints);
		if (last_pc >= 0x5074 && last_pc < 0xC000) {
			status->instructions_user += 1;
			status->cycles_user += cycles;
			// printf("pc=%04x user cycle = %ld\n", last_pc, status->cycles_user);
		}
		if (bpid >= 0) {
			return bpid;
		}
	} while (status->current_cycle_in_frame < status->final_cycle_in_frame);
	status->frame_number += 1;

	return -1;
}

void lib6502_show_next_instruction(emulator_history_t *history)
{
	history_6502_t *entry;
	history_breakpoint_t *b;

	entry = (history_6502_t *)libudis_get_next_entry(history, DISASM_6502_HISTORY);
	if (entry) {
		lib6502_show_current_instruction(entry);
		b = (history_breakpoint_t *)entry;
		b->breakpoint_id = 0;
		b->breakpoint_type = BREAKPOINT_PAUSE_AT_FRAME_START;
		b->disassembler_type = DISASM_NEXT_INSTRUCTION;
		b->disassembler_type_cpu = DISASM_6502_HISTORY;
	}
}

int lib6502_next_frame(input_t *input, output_t *output, breakpoints_t *breakpoints, emulator_history_t *history)
{
	int bpid;
	frame_status_t *status = &output->status;

	if (apple2_mode) {
		memory[0xc000] = input->keychar;
	}
	status->final_cycle_in_frame = cycles_per_frame - 1;
	bpid = libdebugger_calc_frame(&lib6502_calc_frame, memory, (frame_status_t *)output, breakpoints, history);
	lib6502_get_current_state(output);
	return bpid;
}

void lib6502_set_a2_emulation_mode(int mode) {
	if (mode) apple2_mode = 1;
	else apple2_mode = 0;
}
