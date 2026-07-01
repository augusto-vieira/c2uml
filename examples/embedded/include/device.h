#ifndef DEVICE_H
#define DEVICE_H

#define DEVICE_NAME_MAX 32
#define DEVICE_MAX_RETRIES 3

struct device {
    char name[DEVICE_NAME_MAX];
    int id;
    int (*init)(struct device *self);
    int (*read)(struct device *self, void *buf, int size);
    void (*close)(struct device *self);
};

int device_init(struct device *dev, const char *name, int id);
void device_close(struct device *dev);

#endif
