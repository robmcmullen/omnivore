#ifndef LIBEMU_INPUT_H
#define LIBEMU_INPUT_H
#include <stdint.h>


#define INPUT_MOD_SHIFT 1
#define INPUT_MOD_CTRL 2
#define INPUT_MOD_ALT 4
#define INPUT_MOD_OPEN_APPLE 8
#define INPUT_MOD_CLOSED_APPLE 16

typedef struct {
	// KEYBOARD SECTION

	// ascii key value, 0 = no key press, ff = use keycode instead
	uint8_t keychar;

	// keyboard code, keychar has priority, so can be ignored unless keychar is
	// ff
	uint8_t keycode;

	// shift, ctrl, etc; see INPUT_MOD_* constants. */
	uint8_t modifiers;

	// platform dependent non-standard key (option, select, etc.),
	uint8_t special_key;

	// future expansion
	uint8_t unused[4];


	// JOYSTICK SECTION

	// one byte per joystick, each bit indicates a button
	uint8_t joystick_buttons[8];

	// one byte per (digital) joystick, bit 0-3 = up|down|left|right
	uint8_t joysticks[8];


	// ANALOG (MOUSE/PADDLE) SECTION

	// same as joystick buttons
	uint8_t paddle_buttons[8];

	// one byte each, paddles 0 - 7
	uint8_t paddles[8];


	// RESERVED

	// future expansion
	uint8_t reserved[24];
} libemu_input_t; // 64 bytes


#endif /* LIBEMU_INPUT_H */
