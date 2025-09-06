#ifndef _IMGUI_DRAWFRAME
#define _IMGUI_DRAWFRAME

#include "imgui.h"
#include <SDL.h>

void check_event(SDL_Event& event, bool& done);
void draw_frame(ImGuiIO& io, bool& done);

#endif
