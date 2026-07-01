#ifndef CONNECTION_H
#define CONNECTION_H

#include <http_types.h>

typedef struct connection_t connection_t;

typedef void (*connection_on_data_t)(connection_t *conn, const void *data, uint32_t size);
typedef void (*connection_on_close_t)(connection_t *conn);

typedef struct {
    int port;
    connection_on_data_t on_data;
    connection_on_close_t on_close;
    void *user_data;
} connection_args_t;

connection_t *connection_create(const connection_args_t *args);
int connection_send(connection_t *conn, const void *data, uint32_t size);
void connection_close(connection_t *conn);
void connection_destroy(connection_t *conn);

#endif
