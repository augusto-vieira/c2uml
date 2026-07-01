#ifndef ACTUATOR_H
#define ACTUATOR_H

#include "device.h"

struct actuator {
    struct device base;
    int power;
    int active;
};

int actuator_create(struct actuator *a, const char *name, int id, int power);
void actuator_set_active(struct actuator *a, int active);
void actuator_destroy(struct actuator *a);

#endif
