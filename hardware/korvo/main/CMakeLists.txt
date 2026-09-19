idf_component_register(
    SRCS "main.c" "wifi_connect.c" "plusone_ws.c" "korvo_ui.c"
    INCLUDE_DIRS "."
    REQUIRES nvs_flash esp_wifi esp_event esp_http_client json driver esp_netif
)
