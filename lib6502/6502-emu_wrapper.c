#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "6502-emu_wrapper.h"
#include "libdebugger.h"

long cycles_per_frame;


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

void lib6502_clear_state_arrays(void *input, output_t *output)
{
}

void lib6502_configure_state_arrays(void *input, output_t *output) {
	output->frame_status = 0;
	output->cycles_since_power_on = 0;
	output->instructions_since_power_on = 0;
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

int lib6502_step_cpu(frame_status_t *output)
{
	int count;
	uint8_t last_sp;
	intptr_t index;

	last_pc = PC;
	last_sp = SP;

	inst = instructions[memory[PC]];

	write_addr = NULL;
	read_addr = NULL;
	jumping = 0;
	extra_cycles = 0;

	output->memory_access[PC] = 255;
	output->access_type[PC] = ACCESS_TYPE_EXECUTE;
	count = lengths[inst.mode];
	if (count > 1) {
		output->memory_access[PC + 1] = 255;
		output->access_type[PC + 1] = ACCESS_TYPE_EXECUTE;
	}
	if (count > 2) {
		output->memory_access[PC + 2] = 255;
		output->access_type[PC + 2] = ACCESS_TYPE_EXECUTE;
	}

	inst.function();
	if (jumping == 0) PC += count;

	// 7 cycle instructions (e.g. ROL $nnnn,X) don't have a penalty cycle for
	// crossing a page boundary.
	if (inst.cycles == 7) extra_cycles = 0;

	if (read_addr != NULL) {
		index = (intptr_t)read_addr - (intptr_t)(&memory[0]);
		if (index >= 0 && index < MAIN_MEMORY_SIZE) {
			output->memory_access[(uint16_t)index] = 255;
			output->access_type[(uint16_t)index] = ACCESS_TYPE_READ;
		}
	}
	if (write_addr != NULL) {
		index = (intptr_t)write_addr - (intptr_t)(&memory[0]);
		if (index >= 0 && index < MAIN_MEMORY_SIZE) {
			output->memory_access[(uint16_t)index] = 255;
			output->access_type[(uint16_t)index] = ACCESS_TYPE_WRITE;
		}
	}

	/* Maximum of 3 bytes will have changed on the stack */
	if (last_sp < SP) {
		last_sp++;
		output->memory_access[0x100 + last_sp] = 255;
		output->access_type[0x100 + last_sp] = ACCESS_TYPE_READ;
		if (last_sp < SP) {
			last_sp++;
			output->memory_access[0x100 + last_sp] = 255;
			output->access_type[0x100 + last_sp] = ACCESS_TYPE_READ;
		}
		if (last_sp < SP) {
			last_sp++;
			output->memory_access[0x100 + last_sp] = 255;
			output->access_type[0x100 + last_sp] = ACCESS_TYPE_READ;
		}
	}
	else if (last_sp > SP) {
		output->memory_access[0x100 + last_sp] = 255;
		output->access_type[0x100 + last_sp] = ACCESS_TYPE_WRITE;
		last_sp--;
		if (last_sp > SP) {
			output->memory_access[0x100 + last_sp] = 255;
			output->access_type[0x100 + last_sp] = ACCESS_TYPE_WRITE;
			last_sp--;
		}
		if (last_sp > SP) {
			output->memory_access[0x100 + last_sp] = 255;
			output->access_type[0x100 + last_sp] = ACCESS_TYPE_WRITE;
			last_sp--;
		}
	}

	return inst.cycles + extra_cycles;
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
#ifdef DEBUG_CALLBACK
		printf("opcode_type at PC=%04x: opcode=%02x value=%02x\n", last_pc, opcode, value);
#endif
		break;

		default:
		value = 0;
	}
#ifdef DEBUG_CALLBACK
	printf("lib6502_register_callback: token=%d addr=%04x value=%04x\n", token, addr, value);
#endif
	return value;
}

int lib6502_calc_frame(frame_status_t *output, breakpoints_t *breakpoints)
{
	int cycles, bpid, count;

	do {
		last_pc = PC;
		cycles = lib6502_step_cpu(output);
		output->current_instruction_in_frame += 1;
		output->instructions_since_power_on += 1;
		output->current_cycle_in_frame += cycles;
		output->cycles_since_power_on += cycles;
		if (last_pc >= 0x5074 && last_pc < 0xC000) {
			output->instructions_user += 1;
			output->cycles_user += cycles;
			// printf("pc=%04x user cycle = %ld\n", last_pc, output->cycles_user);
		}
		if (SR.bits.brk) {
			/* automatically jump into debugger on BRK */
			PC = last_pc;
			bpid = 0;
		}
		else {
			bpid = libdebugger_check_breakpoints(breakpoints, cycles, &lib6502_register_callback);
		}
		if (bpid >= 0) {
			output->frame_status = FRAME_BREAKPOINT;
			output->breakpoint_id = bpid;
			return bpid;
		}
	} while (output->current_cycle_in_frame < output->final_cycle_in_frame);
	output->frame_number += 1;
	return -1;
}

int lib6502_next_frame(input_t *input, output_t *output, breakpoints_t *breakpoints)
{
	int bpid;

	memory[0xc000] = input->keychar;
	output->final_cycle_in_frame = cycles_per_frame - 1;
	libdebugger_calc_frame(&lib6502_calc_frame, (frame_status_t *)output, breakpoints);
	lib6502_get_current_state(output);
	return bpid;
}
