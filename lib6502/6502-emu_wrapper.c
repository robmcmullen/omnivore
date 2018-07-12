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

void lib6502_clear_state_arrays(void *input, ProcessorState *output)
{
}

void lib6502_configure_state_arrays(void *input, ProcessorState *output) {
	output->frame_finished = 1;
	output->cycles_since_power_on = 0;
}

void lib6502_get_current_state(ProcessorState *buf) {
	buf->A = A;
	buf->X = X;
	buf->Y = Y;
	buf->SP = SP;
	save16(buf->PC, PC);
	buf->SR = SR.byte;
	memcpy(buf->memory, memory, 1<<16);
}

void lib6502_restore_state(ProcessorState *buf) {
	A = buf->A;
	X = buf->X;
	Y = buf->Y;
	SP = buf->SP;
	load16(PC, buf->PC);
	SR.byte = buf->SR;
	memcpy(memory, buf->memory, 1<<16);
}

int lib6502_step_cpu()
{
	inst = instructions[memory[PC]];

	jumping = 0;
	extra_cycles = 0;
	inst.function();
	if (jumping == 0) PC += lengths[inst.mode];

	// 7 cycle instructions (e.g. ROL $nnnn,X) don't have a penalty cycle for
	// crossing a page boundary.
	if (inst.cycles == 7) extra_cycles = 0;

	return inst.cycles + extra_cycles;
}

long lib6502_next_frame(void *input, ProcessorState *output, debugger_t *state)
{
	int cycles;

	if (output->frame_finished) {
		output->frame_finished = 0;
		output->current_cycle_in_frame = 0;
		output->final_cycle_in_frame = cycles_per_frame - 1;
	}
	output->breakpoint_hit = 0;
	do {
		if (libdebugger_check_breakpoints(state, PC) >= 0) {
			output->breakpoint_hit = 1;
			goto get_state;
		}
		cycles = lib6502_step_cpu();
		output->current_cycle_in_frame += cycles;
		output->cycles_since_power_on += cycles;
	} while (output->current_cycle_in_frame < output->final_cycle_in_frame);
	output->frame_number += 1;
	output->frame_finished = 1;

get_state:
	lib6502_get_current_state(output);
	return cycles;
}
