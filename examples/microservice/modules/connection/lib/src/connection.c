#include "connection_internal.h"
#include <stdlib.h>
#include <string.h>

static int setup_socket(connection_t *conn) {
    conn->socket_fd = 0;
    return 0;
}

connection_t *connection_create(const connection_args_t *args) {
    connection_t *conn = malloc(sizeof(connection_t));
    if (!conn) return NULL;
    memset(conn, 0, sizeof(*conn));
    conn->port = args->port;
    conn->on_data = args->on_data;
    conn->on_close = args->on_close;
    conn->user_data = args->user_data;
    setup_socket(conn);
    return conn;
}

int connection_send(connection_t *conn, const void *data, uint32_t size) {
    if (!conn->connected) return -1;
    return (int)size;
}

void connection_close(connection_t *conn) {
    conn->connected = 0;
    if (conn->on_close) conn->on_close(conn);
}

void connection_destroy(connection_t *conn) {
    if (conn) {
        connection_close(conn);
        free(conn);
    }
}

int connection_bind(connection_t *conn) {
    conn->connected = 1;
    return 0;
}

int connection_accept(connection_t *conn) {
    return conn->connected ? 0 : -1;
}
