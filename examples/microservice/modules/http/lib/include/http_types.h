#ifndef HTTP_TYPES_H
#define HTTP_TYPES_H

#include <stdint.h>

typedef enum {
    HTTP_GET,
    HTTP_POST,
    HTTP_PUT,
    HTTP_DELETE
} http_method_t;

typedef enum {
    HTTP_200_OK,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_ERROR
} http_status_t;

typedef struct {
    char key[64];
    char value[256];
} http_header_t;

typedef union {
    char text[1024];
    uint8_t binary[1024];
} http_body_t;

typedef union {
    int integer;
    float decimal;
    char string[256];
} http_config_value_t;

typedef struct {
    char key[64];
    http_config_value_t value;
} http_config_t;

typedef struct {
    http_method_t method;
    char path[256];
    http_header_t headers[16];
    uint8_t header_count;
    http_body_t body;
    uint32_t body_size;
} http_request_t;

typedef struct {
    http_status_t status;
    http_header_t headers[16];
    uint8_t header_count;
    char body[4096];
    uint32_t body_size;
} http_response_t;

typedef void (*http_handler_t)(const http_request_t *req, http_response_t *res);

#endif
