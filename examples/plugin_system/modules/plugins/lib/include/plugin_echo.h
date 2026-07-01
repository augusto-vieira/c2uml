#ifndef PLUGIN_ECHO_H
#define PLUGIN_ECHO_H

#include <plugin_core.h>

typedef struct {
    char prefix[32];
    int echo_count;
} echo_context_t;

plugin_t echo_plugin_create(const char *prefix);

#endif
