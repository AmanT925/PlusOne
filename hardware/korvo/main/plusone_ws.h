#pragma once
#include "esp_err.h"
#include <stdbool.h>

typedef void (*plusone_whisper_cb_t)(const char *text, const char *audio_url);

esp_err_t plusone_ws_start(plusone_whisper_cb_t on_whisper);
esp_err_t plusone_ws_send_utterance(const char *visibility, const char *text);
bool plusone_ws_connected(void);

/** HTTP POST /rooms/{room}/audio with transcript bypass (Phase 1–2). */
esp_err_t plusone_post_audio_bypass(const char *visibility, const char *transcript);
