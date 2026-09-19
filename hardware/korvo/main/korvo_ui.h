#pragma once

#include <stdbool.h>

#include "esp_err.h"

typedef enum {
    KORVO_LED_IDLE = 0,
    KORVO_LED_LISTEN,
    KORVO_LED_PRIVATE,
    KORVO_LED_PLAYING,
} korvo_led_state_t;

esp_err_t korvo_ui_init(void);
void korvo_ui_set_led(korvo_led_state_t state);

/** Returns true while the whisper (hold) button is pressed. GPIO stub — remap for Korvo BSP. */
bool korvo_ui_whisper_held(void);

/**
 * Play whisper audio on the 3.5 mm jack ONLY (never the speaker amp).
 * Phase 2: download audio_url via HTTP and feed ES8311.
 * Stub logs the URL until codec bring-up is done.
 */
esp_err_t korvo_ui_play_whisper(const char *text, const char *audio_url);
