#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "6502-emu_wrapper.h"

long cycles_per_frame;


void lib6502_init_cpu(float frequency_mhz, float refresh_rate_hz) {
	A = 0;
	X = 0;
	Y = 0;
	SP = 0xff;
	SR.byte = 0;
	PC = 0xfffe;
	memset(memory, 0, sizeof(memory));

	cycles_per_frame = (long)((frequency_mhz * 1000000.0) / refresh_rate_hz);
}

void lib6502_get_current_state(ProcessorState *buf) {
	buf->A = A;
	buf->X = X;
	buf->Y = Y;
	buf->SP = SP;
	buf->PC = PC;
	buf->SR = SR.byte;
	buf->total_cycles = total_cycles;
	memcpy(buf->memory, memory, 1<<16);
}

void lib6502_restore_state(ProcessorState *buf) {
	A = buf->A;
	X = buf->X;
	Y = buf->Y;
	SP = buf->SP;
	PC = buf->PC;
	SR.byte = buf->SR;
	total_cycles = buf->total_cycles;
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

	total_cycles += inst.cycles + extra_cycles;
	return inst.cycles + extra_cycles;
}

long lib6502_next_frame()
{
	long cycles = 0;

	do {
		cycles += lib6502_step_cpu();
	} while (cycles < cycles_per_frame);
	return cycles;
}
