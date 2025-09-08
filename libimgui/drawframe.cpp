// Dear ImGui: standalone example application for SDL2 + OpenGL
// (SDL is a cross-platform general purpose library for handling windows, inputs, OpenGL/Vulkan/Metal graphics context creation, etc.)

// Learn about Dear ImGui:
// - FAQ                  https://dearimgui.com/faq
// - Getting Started      https://dearimgui.com/getting-started
// - Documentation        https://dearimgui.com/docs (same as your local docs/ folder).
// - Introduction, links and more at the top of imgui.cpp

#include "imgui.h"
#include "imgui_internal.h"
#include <SDL.h>
#include <SDL_events.h>
#include <SDL_keyboard.h>
#include <SDL_keycode.h>
#include "drawframe.h"

void check_event(SDL_Event &event, bool &done) {
    if (event.type == SDL_KEYDOWN) {
        if (event.key.keysym.sym == SDLK_q)
            done = true;
    }
}

// Our state
bool show_demo_window = true;
bool show_another_window = false;

void draw_frame(ImGuiIO& io, bool& done) {
    if (ImGui::BeginMainMenuBar()) {
        if (ImGui::BeginMenu("File"))
        {
            // Create menu items
            if (ImGui::MenuItem("New", "Ctrl+N"))
            {
                // Handle when the "New" menu item is selected
            }
            if (ImGui::MenuItem("Open", "Ctrl+O"))
            {
                // Handle when the "Open" menu item is selected
            }
            if (ImGui::MenuItem("Save", "Ctrl+S"))
            {
                // Handle when the "Save" menu item is selected
            }
            ImGui::Separator();
            if (ImGui::MenuItem("Quit", "Ctrl+Q")) {
                done = true;
            }
            ImGui::EndMenu();
        }
        ImGui::EndMainMenuBar();
    }

    // 1. Show the big demo window (Most of the sample code is in ImGui::ShowDemoWindow()! You can browse its code to learn more about Dear ImGui!).
    if (show_demo_window)
        ImGui::ShowDemoWindow(&show_demo_window);

    // 2. Show a simple window that we create ourselves. We use a Begin/End pair to create a named window.
    {
        static float f = 0.0f;
        static int counter = 0;

        ImGui::Begin("Hello, world!");                          // Create a window called "Hello, world!" and append into it.

        ImGui::Text("This is some useful text.");               // Display some text (you can use a format strings too)
        ImGui::Checkbox("Demo Window", &show_demo_window);      // Edit bools storing our window open/close state
        ImGui::Checkbox("Another Window", &show_another_window);

        ImGui::SliderFloat("float", &f, 0.0f, 1.0f);            // Edit 1 float using a slider from 0.0f to 1.0f

        if (ImGui::Button("Button"))                            // Buttons return true when clicked (most widgets return true when edited/activated)
            counter++;
        ImGui::SameLine();
        ImGui::Text("counter = %d", counter);
        ImGui::End();
    }

    ImGuiViewport * viewport = ImGui::GetMainViewport();
    float heightSideBar = ImGui::GetFrameHeight();

    if(ImGui::BeginViewportSideBar("StatusBar", viewport, ImGuiDir_Down, heightSideBar, ImGuiWindowFlags_NoScrollbar | ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_MenuBar)) {
        if(ImGui::BeginMenuBar()) {
            ImGui::Text("Application average %.3f ms/frame (%.1f FPS)", 1000.0f / io.Framerate, io.Framerate);
            ImGui::EndMenuBar();
        }
        ImGui::End();
    }

    // 3. Show another simple window.
    if (show_another_window)
    {
        ImGui::Begin("Another Window", &show_another_window);   // Pass a pointer to our bool variable (the window will have a closing button that will clear the bool when clicked)
        ImGui::Text("Hello from another window!");
        if (ImGui::Button("Close Me"))
            show_another_window = false;
        ImGui::End();
    }

}
