#ifndef CONNECTION_INTERNAL_H
#define CONNECTION_INTERNAL_H

#include <connection.h>

struct connection_t {
    int socket_fd;
    int port;
    int connected;
    connection_on_data_t on_data;
    connection_on_close_t on_close;
    void *user_data;
    char recv_buffer[4096];
};

int connection_bind(connection_t *conn);
int connection_accept(connection_t *conn);

#endif
