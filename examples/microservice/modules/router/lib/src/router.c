#include "router.h"
#include <string.h>

void router_init(router_t *r) {
    r->count = 0;
    memset(r->routes, 0, sizeof(r->routes));
}

int router_add(router_t *r, http_method_t method, const char *path, http_handler_t handler) {
    if (r->count >= ROUTER_MAX_ROUTES) return -1;
    r->routes[r->count].method = method;
    strncpy(r->routes[r->count].path, path, 255);
    r->routes[r->count].handler = handler;
    r->count++;
    return 0;
}

http_handler_t router_match(const router_t *r, const http_request_t *req) {
    for (int i = 0; i < r->count; i++) {
        if (r->routes[i].method == req->method &&
            strcmp(r->routes[i].path, req->path) == 0) {
            return r->routes[i].handler;
        }
    }
    return NULL;
}
