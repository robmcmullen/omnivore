#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "6502-emu_wrapper.h"

long cycles_per_frame;
uint32_t frame_number;


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
	frame_number = 0;

	lib6502_init_debug_kernel();
}

void lib6502_prepare_arrays(void *input, ProcessorState *output)
{
	output->frame_number = 0;
}

void lib6502_get_current_state(ProcessorState *buf) {
	printf("addr=%lx A=%x X=%x Y=%x SP=%x PC=%x\n", buf, A, X, Y, SP, PC);
	buf->A = A;
	buf->X = X;
	buf->Y = Y;
	buf->SP = SP;
	buf->PC = PC;
	buf->SR = SR.byte;
	buf->total_cycles = total_cycles;
	buf->frame_number = frame_number;
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
	frame_number = buf->frame_number;
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
	frame_number += 1;
	return cycles;
}
