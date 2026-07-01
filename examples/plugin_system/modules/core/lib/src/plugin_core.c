#include "plugin_core.h"
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

static int find_index(plugin_manager_t *mgr, const char *name) {
    for (int i = 0; i < mgr->count; i++) {
        if (strcmp(mgr->plugins[i].name, name) == 0) return i;
    }
    return -1;
}

void plugin_manager_init(plugin_manager_t *mgr) {
    memset(mgr, 0, sizeof(*mgr));
    mgr->log_level = PLUGIN_LOG_INFO;
}

int plugin_manager_load(plugin_manager_t *mgr, const plugin_t *plugin) {
    if (mgr->count >= PLUGIN_MAX_PLUGINS) return -1;
    mgr->plugins[mgr->count] = *plugin;
    mgr->plugins[mgr->count].state = PLUGIN_STATE_LOADED;
    if (plugin->hooks.on_load) {
        plugin->hooks.on_load(plugin->context);
        mgr->plugins[mgr->count].state = PLUGIN_STATE_ACTIVE;
    }
    mgr->count++;
    return 0;
}

int plugin_manager_unload(plugin_manager_t *mgr, const char *name) {
    int idx = find_index(mgr, name);
    if (idx < 0) return -1;
    if (mgr->plugins[idx].hooks.on_unload)
        mgr->plugins[idx].hooks.on_unload(mgr->plugins[idx].context);
    mgr->plugins[idx].state = PLUGIN_STATE_UNLOADED;
    return 0;
}

plugin_t *plugin_manager_find(plugin_manager_t *mgr, const char *name) {
    int idx = find_index(mgr, name);
    return idx >= 0 ? &mgr->plugins[idx] : NULL;
}

void plugin_manager_destroy(plugin_manager_t *mgr) {
    for (int i = 0; i < mgr->count; i++) {
        if (mgr->plugins[i].state == PLUGIN_STATE_ACTIVE)
            plugin_manager_unload(mgr, mgr->plugins[i].name);
    }
    mgr->count = 0;
}

void plugin_log_write(plugin_log_level_t level, const char *file, int line, const char *fmt, ...) {
    const char *labels[] = {"ERROR", "WARN", "INFO", "DEBUG"};
    va_list args;
    va_start(args, fmt);
    fprintf(stderr, "[%s] %s:%d: ", labels[level], file, line);
    vfprintf(stderr, fmt, args);
    fprintf(stderr, "\n");
    va_end(args);
}
