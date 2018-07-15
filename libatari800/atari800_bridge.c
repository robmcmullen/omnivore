#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "libdebugger.h"

#include "log.h"
#include "input.h"
#include "platform.h"
#include "libatari800/main.h"
#include "libatari800/init.h"
#include "libatari800/input.h"
#include "libatari800/video.h"
#include "libatari800/statesav.h"


int PLATFORM_Exit(int run_monitor)
{
	printf("HERE IN atari800_bridge PLATFORM_Exit!\n");
	Log_flushlog();

	LIBATARI800_Output_array->breakpoint_id = 0;

	return 1;  /* always continue. Leave it to the client to exit */
}

int a8bridge_calc_frame(frame_status_t *output, breakpoints_t *breakpoints) {
       LIBATARI800_Mouse();
       LIBATARI800_Frame();
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
	INPUT_key_code = PLATFORM_Keyboard();

	libdebugger_calc_frame(&a8bridge_calc_frame, (frame_status_t *)output, breakpoints);

	LIBATARI800_Mouse();
	LIBATARI800_Frame();
	LIBATARI800_StateSave();
	if (output->frame_status == FRAME_FINISHED) {
		PLATFORM_DisplayScreen();
	}
	return bpid;
}
