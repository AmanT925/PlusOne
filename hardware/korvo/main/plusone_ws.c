#include "plusone_ws.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "esp_log.h"
#include "esp_websocket_client.h"
#include "freertos/FreeRTOS.h"

static const char *TAG = "plusone_ws";
static esp_websocket_client_handle_t s_ws;
static plusone_whisper_cb_t s_on_whisper;
static bool s_connected;

static void handle_json(const char *data, int len)
{
    cJSON *root = cJSON_ParseWithLength(data, len);
    if (!root) {
        return;
    }
    const cJSON *type = cJSON_GetObjectItem(root, "type");
    if (cJSON_IsString(type) && strcmp(type->valuestring, "whisper") == 0) {
        const cJSON *text = cJSON_GetObjectItem(root, "text");
        const cJSON *audio = cJSON_GetObjectItem(root, "audio_url");
        if (s_on_whisper && cJSON_IsString(text)) {
            s_on_whisper(text->valuestring, cJSON_IsString(audio) ? audio->valuestring : NULL);
        }
    }
    cJSON_Delete(root);
}

static void ws_event(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    switch (event_id) {
    case WEBSOCKET_EVENT_CONNECTED:
        s_connected = true;
        ESP_LOGI(TAG, "connected");
        break;
    case WEBSOCKET_EVENT_DISCONNECTED:
        s_connected = false;
        ESP_LOGW(TAG, "disconnected");
        break;
    case WEBSOCKET_EVENT_DATA:
        if (data->op_code == 0x1 && data->data_ptr && data->data_len > 0) {
            handle_json(data->data_ptr, data->data_len);
        }
        break;
    default:
        break;
    }
}

esp_err_t plusone_ws_start(plusone_whisper_cb_t on_whisper)
{
    s_on_whisper = on_whisper;
    char url[192];
#if CONFIG_PLUSONE_USE_TLS
    snprintf(url, sizeof(url), "wss://%s:%d/ws/%s/%s", CONFIG_PLUSONE_HOST, CONFIG_PLUSONE_PORT,
             CONFIG_PLUSONE_ROOM, CONFIG_PLUSONE_USER);
#else
    snprintf(url, sizeof(url), "ws://%s:%d/ws/%s/%s", CONFIG_PLUSONE_HOST, CONFIG_PLUSONE_PORT,
             CONFIG_PLUSONE_ROOM, CONFIG_PLUSONE_USER);
#endif
    ESP_LOGI(TAG, "connecting %s", url);

    esp_websocket_client_config_t cfg = {
        .uri = url,
        .reconnect_timeout_ms = 5000,
        .network_timeout_ms = 10000,
    };
    s_ws = esp_websocket_client_init(&cfg);
    if (!s_ws) {
        return ESP_FAIL;
    }
    esp_websocket_register_events(s_ws, WEBSOCKET_EVENT_ANY, ws_event, NULL);
    return esp_websocket_client_start(s_ws);
}

bool plusone_ws_connected(void)
{
    return s_connected && s_ws && esp_websocket_client_is_connected(s_ws);
}

esp_err_t plusone_ws_send_utterance(const char *visibility, const char *text)
{
    if (!plusone_ws_connected()) {
        return ESP_ERR_INVALID_STATE;
    }
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "type", "utterance");
    cJSON_AddStringToObject(root, "visibility", visibility);
    cJSON_AddStringToObject(root, "text", text);
    char *payload = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    if (!payload) {
        return ESP_ERR_NO_MEM;
    }
    int sent = esp_websocket_client_send_text(s_ws, payload, strlen(payload), portMAX_DELAY);
    free(payload);
    return sent > 0 ? ESP_OK : ESP_FAIL;
}

esp_err_t plusone_post_audio_bypass(const char *visibility, const char *transcript)
{
    ESP_LOGW(TAG, "audio bypass via WS utterance until multipart helper lands");
    return plusone_ws_send_utterance(visibility, transcript);
}
