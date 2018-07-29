
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"

#include "log.h"
#include "input.h"
#include "platform.h"
#include "cpu.h"
#ifdef SOUND
#include "sound.h"
#endif
#include "libatari800/main.h"
#include "libatari800/init.h"
#include "libatari800/input.h"
#include "libatari800/video.h"
#include "libatari800/statesav.h"

#include "tinycthread.h"


mtx_t calculating_frame;
cnd_t talking_stick;
thrd_t frame_thread;

breakpoints_t *LIBATARI800_Breakpoints = NULL;

int threaded_frame(void *arg);


int a8bridge_init(void) {
	int err;

	err = mtx_init(&calculating_frame, mtx_plain);
	if (err == thrd_success) {
		err = cnd_init(&talking_stick);
	}
	if (err == thrd_success) {
		err = thrd_create(&frame_thread, threaded_frame, (void *)NULL);
	}
	if (err == thrd_success) {
		printf("a8bridge_init: successfully created threading context\n");
	}
	else {
		printf("a8bridge_init: failed creating threading context: %d\n", err);
	}
	return err;
}


int a8bridge_register_callback(uint16_t token, uint16_t addr) {
	int value;

	switch (token) {
		case REG_A:
		value = CPU_regA;
		break;

		case REG_X:
		value = CPU_regX;
		break;

		case REG_Y:
		value = CPU_regY;
		break;

		case REG_PC:
		value = CPU_regPC;
		break;

		default:
		value = 0;
	}
	printf("a8bridge_register_callback: token=%d addr=%04x value=%04x\n", token, addr, value);
	return value;
}



int LIBATARI800_CheckBreakpoints() {
	int bpid;
	int cycles = 0; /*fixme*/

	bpid = libdebugger_check_breakpoints(LIBATARI800_Breakpoints, cycles, &a8bridge_register_callback);
	if (bpid >= 0) {
		LIBATARI800_Output_array->frame_status = FRAME_BREAKPOINT;
		LIBATARI800_Output_array->breakpoint_id = bpid;
		return bpid;
	}
	return -1;
}


int PLATFORM_Exit(int run_monitor)
{
	int err;

	Log_flushlog();

	LIBATARI800_Output_array->breakpoint_id = 0;

	err = cnd_broadcast(&talking_stick);
	if (err == thrd_error) {
		printf("cnd_broadcast failed in PLATFORM_Exit\n");
	}
	else {
		printf("PLATFORM_Exit giving up the talking stick\n");
	}

	printf("Waiting for main thread to handle breakpoint...\n");

	err = cnd_wait(&talking_stick, &calculating_frame);
	if (err == thrd_error) {
		printf("cnd_wait failed in PLATFORM_Exit\n");
	}
	else {
		printf("PLATFORM_Exit has the talking stick\n");
	}
	return 1;  /* always continue. Leave it to the client to exit */
}


int threaded_frame(void *arg) {
	int err = thrd_success;

	while (err == thrd_success) {
		err = cnd_wait(&talking_stick, &calculating_frame);
		if (err == thrd_error) {
			printf("cnd_wait failed in threaded_frame\n");
		}
		else {
			printf("threaded_frame has the talking stick\n");
		}

		LIBATARI800_Mouse();

	#ifdef PBI_BB
		PBI_BB_Frame(); /* just to make the menu key go up automatically */
	#endif
	#if defined(PBI_XLD) || defined (VOICEBOX)
		VOTRAXSND_Frame(); /* for the Votrax */
	#endif
		Devices_Frame();
		INPUT_Frame();
		GTIA_Frame();
		ANTIC_Frame(TRUE);
		INPUT_DrawMousePointer();
		Screen_DrawAtariSpeed(Util_time());
		Screen_DrawDiskLED();
		Screen_Draw1200LED();
		POKEY_Frame();
	#ifdef SOUND
		Sound_Update();
	#endif
		Atari800_nframes++;

		err = cnd_broadcast(&talking_stick);
		if (err == thrd_error) {
			printf("cnd_broadcast failed in threaded_frame\n");
		}
		else {
			printf("threaded_frame giving up the talking stick\n");
		}
	}
	printf("threaded_frame exited with %d\n", err);
	return err;
}


int a8bridge_calc_frame(frame_status_t *output, breakpoints_t *breakpoints) {
	int err;

	err = cnd_broadcast(&talking_stick);
	if (err == thrd_error) {
		printf("cnd_broadcast failed in a8bridge_calc_frame\n");
	}
	else {
		printf("a8bridge_calc_frame giving up the talking stick\n");
	}

	printf("a8bridge_calc_frame waiting for frame or breakpoint\n");

	err = cnd_wait(&talking_stick, &calculating_frame);
	if (err == thrd_error) {
		printf("cnd_wait failed in a8bridge_calc_frame\n");
	}
	else {
		printf("a8bridge_calc_frame has the talking stick\n");
	}
	return -1;
}

int a8bridge_next_frame(input_template_t *input, output_template_t *output, breakpoints_t *breakpoints)
{
	int bpid;

	LIBATARI800_Input_array = input;
	LIBATARI800_Output_array = output;
	LIBATARI800_Video_array = output->video;
	LIBATARI800_Sound_array = output->audio;
	LIBATARI800_Save_state = output->state;
	LIBATARI800_Breakpoints = breakpoints;
	INPUT_key_code = PLATFORM_Keyboard();

	libdebugger_calc_frame(&a8bridge_calc_frame, (frame_status_t *)output, breakpoints);

	LIBATARI800_StateSave();
	if (output->frame_status == FRAME_FINISHED) {
		PLATFORM_DisplayScreen();
	}
	return bpid;
}


