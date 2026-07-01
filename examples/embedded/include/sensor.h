#ifndef SENSOR_H
#define SENSOR_H

#include "device.h"

#define SENSOR_TEMP_OFFSET 40

struct sensor {
    struct device base;
    int channel;
    float last_value;
};

int sensor_create(struct sensor *s, const char *name, int id, int channel);
float sensor_read_value(struct sensor *s);
void sensor_destroy(struct sensor *s);

#endif
