#include "actuator.h"

static void actuator_hw_close(struct device *self) {
    struct actuator *a = (struct actuator *)self;
    a->active = 0;
    a->power = 0;
}

int actuator_create(struct actuator *a, const char *name, int id, int power) {
    device_init(&a->base, name, id);
    a->base.close = actuator_hw_close;
    a->power = power;
    a->active = 0;
    return 0;
}

void actuator_set_active(struct actuator *a, int active) {
    a->active = active;
}

void actuator_destroy(struct actuator *a) {
    device_close(&a->base);
}
