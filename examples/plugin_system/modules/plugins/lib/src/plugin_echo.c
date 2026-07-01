#include "plugin_echo.h"
#include <string.h>
#include <stdio.h>

static echo_context_t echo_ctx;

static int echo_on_load(void *ctx) {
    echo_context_t *e = (echo_context_t *)ctx;
    e->echo_count = 0;
    return 0;
}

static void echo_on_unload(void *ctx) {
    echo_context_t *e = (echo_context_t *)ctx;
    plugin_log(PLUGIN_LOG_INFO, "echo unloaded, total: %d", e->echo_count);
}

static int echo_on_message(void *ctx, const void *data, uint32_t size) {
    echo_context_t *e = (echo_context_t *)ctx;
    printf("%s: %.*s\n", e->prefix, size, (const char *)data);
    e->echo_count++;
    return 0;
}

plugin_t echo_plugin_create(const char *prefix) {
    plugin_t p;
    memset(&p, 0, sizeof(p));
    strncpy(p.name, "echo", PLUGIN_MAX_NAME - 1);
    strncpy(echo_ctx.prefix, prefix, 31);
    p.hooks.on_load = echo_on_load;
    p.hooks.on_unload = echo_on_unload;
    p.hooks.on_message = echo_on_message;
    p.context = &echo_ctx;
    return p;
}
