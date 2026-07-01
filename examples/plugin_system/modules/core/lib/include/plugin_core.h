#ifndef PLUGIN_CORE_H
#define PLUGIN_CORE_H

#include <stdint.h>

#define PLUGIN_MAX_NAME 64
#define PLUGIN_MAX_PLUGINS 16
#define PLUGIN_VERSION_MAJOR 1
#define PLUGIN_VERSION_MINOR 0

#define plugin_log(level, fmt, ...) \
    plugin_log_write(level, __FILE__, __LINE__, fmt)

typedef enum {
    PLUGIN_LOG_ERROR,
    PLUGIN_LOG_WARN,
    PLUGIN_LOG_INFO,
    PLUGIN_LOG_DEBUG
} plugin_log_level_t;

typedef enum {
    PLUGIN_STATE_UNLOADED,
    PLUGIN_STATE_LOADED,
    PLUGIN_STATE_ACTIVE,
    PLUGIN_STATE_ERROR
} plugin_state_t;

typedef struct {
    char name[PLUGIN_MAX_NAME];
    uint32_t version;
    plugin_state_t state;
    struct plugin_hooks {
        int (*on_load)(void *ctx);
        void (*on_unload)(void *ctx);
        int (*on_message)(void *ctx, const void *data, uint32_t size);
    } hooks;
    void *context;
} plugin_t;

typedef struct {
    plugin_t plugins[PLUGIN_MAX_PLUGINS];
    int count;
    plugin_log_level_t log_level;
} plugin_manager_t;

void plugin_manager_init(plugin_manager_t *mgr);
int plugin_manager_load(plugin_manager_t *mgr, const plugin_t *plugin);
int plugin_manager_unload(plugin_manager_t *mgr, const char *name);
plugin_t *plugin_manager_find(plugin_manager_t *mgr, const char *name);
void plugin_manager_destroy(plugin_manager_t *mgr);

void plugin_log_write(plugin_log_level_t level, const char *file, int line, const char *fmt, ...);

#endif
