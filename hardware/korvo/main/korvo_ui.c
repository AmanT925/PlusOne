#include "korvo_ui.h"

#include "driver/gpio.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "korvo_ui";

// Remap these to the Korvo-1 function button GPIOs from the Espressif BSP.
#ifndef KORVO_WHISPER_BTN_GPIO
#define KORVO_WHISPER_BTN_GPIO 0
#endif

esp_err_t korvo_ui_init(void)
{
    gpio_config_t io = {
        .pin_bit_mask = 1ULL << KORVO_WHISPER_BTN_GPIO,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io));
    ESP_LOGI(TAG, "UI ready (whisper btn GPIO %d — remap for Korvo BSP)", KORVO_WHISPER_BTN_GPIO);
    return ESP_OK;
}

void korvo_ui_set_led(korvo_led_state_t state)
{
    const char *name = "idle";
    switch (state) {
    case KORVO_LED_LISTEN:
        name = "listen";
        break;
    case KORVO_LED_PRIVATE:
        name = "private";
        break;
    case KORVO_LED_PLAYING:
        name = "playing";
        break;
    default:
        break;
    }
    // TODO: drive WS2812C strip on ESP32-Korvo-Mic sub-board.
    ESP_LOGI(TAG, "LED -> %s", name);
}

bool korvo_ui_whisper_held(void)
{
    // Active-low with pull-up (Boot button on many ESP32 boards).
    return gpio_get_level(KORVO_WHISPER_BTN_GPIO) == 0;
}

esp_err_t korvo_ui_play_whisper(const char *text, const char *audio_url)
{
    korvo_ui_set_led(KORVO_LED_PLAYING);
    ESP_LOGI(TAG, "WHISPER (headphones only): %s", text ? text : "");
    if (audio_url && audio_url[0]) {
        ESP_LOGI(TAG, "TODO play MP3 from %s via ES8311 -> 3.5mm jack", audio_url);
        // Phase 2: esp_http_client download -> decode -> I2S out on headphone path.
        // Do NOT enable the class-D speaker amp for private audio.
    }
    vTaskDelay(pdMS_TO_TICKS(50));
    korvo_ui_set_led(KORVO_LED_IDLE);
    return ESP_OK;
}
