#include <stdio.h>
#include <string.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "korvo_ui.h"
#include "plusone_ws.h"
#include "wifi_connect.h"

static const char *TAG = "plusone_korvo";

static void on_whisper(const char *text, const char *audio_url)
{
    korvo_ui_play_whisper(text, audio_url);
}

static void button_task(void *arg)
{
    bool was_held = false;
    char visibility[64];
    snprintf(visibility, sizeof(visibility), "private:%s", CONFIG_PLUSONE_USER);

    while (1) {
        bool held = korvo_ui_whisper_held();
        if (held && !was_held) {
            korvo_ui_set_led(KORVO_LED_PRIVATE);
            ESP_LOGI(TAG, "whisper hold start (capture audio in Phase 3)");
        }
        if (!held && was_held) {
            // Phase 1–2: send a canned private constraint so the loop is demonstrable
            // without I2S capture. Phase 3: flush WAV buffer -> POST /rooms/.../audio.
            const char *text = "I can't do more than 150 this month";
            ESP_LOGI(TAG, "whisper release -> send private utterance");
            if (plusone_ws_send_utterance(visibility, text) != ESP_OK) {
                ESP_LOGW(TAG, "send failed (ws down?)");
            }
            korvo_ui_set_led(KORVO_LED_IDLE);
        }
        was_held = held;
        vTaskDelay(pdMS_TO_TICKS(30));
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "Plus One Korvo — room=%s user=%s", CONFIG_PLUSONE_ROOM, CONFIG_PLUSONE_USER);
    ESP_ERROR_CHECK(korvo_ui_init());
    korvo_ui_set_led(KORVO_LED_IDLE);

    if (wifi_connect_sta() != ESP_OK) {
        ESP_LOGE(TAG, "Wi-Fi failed; halt");
        return;
    }

    ESP_ERROR_CHECK(plusone_ws_start(on_whisper));

    // Wait for socket
    for (int i = 0; i < 50 && !plusone_ws_connected(); ++i) {
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    if (!plusone_ws_connected()) {
        ESP_LOGW(TAG, "WS not up yet; button task will retry sends");
    }

    xTaskCreate(button_task, "btn", 4096, NULL, 5, NULL);
    ESP_LOGI(TAG, "ready — hold whisper button, listen on headphones");
}
