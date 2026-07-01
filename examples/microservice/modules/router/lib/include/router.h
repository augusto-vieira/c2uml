#ifndef ROUTER_H
#define ROUTER_H

#include <http_types.h>

#define ROUTER_MAX_ROUTES 32

typedef struct {
    http_method_t method;
    char path[256];
    http_handler_t handler;
} route_t;

typedef struct {
    route_t routes[ROUTER_MAX_ROUTES];
    int count;
} router_t;

void router_init(router_t *r);
int router_add(router_t *r, http_method_t method, const char *path, http_handler_t handler);
http_handler_t router_match(const router_t *r, const http_request_t *req);

#endif
