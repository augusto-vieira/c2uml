#include "device.h"
#include <string.h>

static int default_init(struct device *self) {
    return 0;
}

static int default_read(struct device *self, void *buf, int size) {
    return -1;
}

static void default_close(struct device *self) {
    self->id = -1;
}

int device_init(struct device *dev, const char *name, int id) {
    strncpy(dev->name, name, DEVICE_NAME_MAX - 1);
    dev->id = id;
    dev->init = default_init;
    dev->read = default_read;
    dev->close = default_close;
    return 0;
}

void device_close(struct device *dev) {
    if (dev->close) dev->close(dev);
}
