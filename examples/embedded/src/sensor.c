#include "sensor.h"

static int sensor_hw_read(struct device *self, void *buf, int size) {
    struct sensor *s = (struct sensor *)self;
    float *out = (float *)buf;
    *out = s->last_value + SENSOR_TEMP_OFFSET;
    return sizeof(float);
}

int sensor_create(struct sensor *s, const char *name, int id, int channel) {
    device_init(&s->base, name, id);
    s->base.read = sensor_hw_read;
    s->channel = channel;
    s->last_value = 0.0f;
    return 0;
}

float sensor_read_value(struct sensor *s) {
    float val;
    s->base.read(&s->base, &val, sizeof(val));
    s->last_value = val;
    return val;
}

void sensor_destroy(struct sensor *s) {
    device_close(&s->base);
}
