#ifndef ENGINE_H
#define ENGINE_H

#include <stdint.h>

#define ENGINE_MAX_ENTITIES 256
#define ENGINE_TICK_MS 16

typedef enum {
    ENTITY_STATE_IDLE,
    ENTITY_STATE_ACTIVE,
    ENTITY_STATE_DEAD
} entity_state_t;

typedef enum {
    ENTITY_TYPE_PLAYER,
    ENTITY_TYPE_ENEMY,
    ENTITY_TYPE_ITEM
} entity_type_t;

typedef struct {
    float x;
    float y;
} vec2_t;

typedef struct entity_t {
    int id;
    entity_type_t type;
    entity_state_t state;
    vec2_t position;
    void (*on_update)(struct entity_t *self, float dt);
    void (*on_collision)(struct entity_t *self, struct entity_t *other);
} entity_t;

typedef struct {
    entity_t entities[ENGINE_MAX_ENTITIES];
    int count;
    float time;
} world_t;

void world_init(world_t *w);
int world_add_entity(world_t *w, entity_t *e);
void world_update(world_t *w, float dt);
void world_destroy(world_t *w);

void entity_init(entity_t *e, int id, entity_type_t type, vec2_t pos);

#endif
