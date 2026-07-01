#include "engine.h"
#include <string.h>

static void check_collisions(world_t *w) {
    for (int i = 0; i < w->count; i++) {
        for (int j = i + 1; j < w->count; j++) {
            entity_t *a = &w->entities[i];
            entity_t *b = &w->entities[j];
            float dx = a->position.x - b->position.x;
            float dy = a->position.y - b->position.y;
            if (dx * dx + dy * dy < 1.0f) {
                if (a->on_collision) a->on_collision(a, b);
                if (b->on_collision) b->on_collision(b, a);
            }
        }
    }
}

void world_init(world_t *w) {
    memset(w, 0, sizeof(*w));
}

int world_add_entity(world_t *w, entity_t *e) {
    if (w->count >= ENGINE_MAX_ENTITIES) return -1;
    w->entities[w->count++] = *e;
    return 0;
}

void world_update(world_t *w, float dt) {
    w->time += dt;
    for (int i = 0; i < w->count; i++) {
        if (w->entities[i].state == ENTITY_STATE_ACTIVE && w->entities[i].on_update)
            w->entities[i].on_update(&w->entities[i], dt);
    }
    check_collisions(w);
}

void world_destroy(world_t *w) {
    w->count = 0;
    w->time = 0;
}

void entity_init(entity_t *e, int id, entity_type_t type, vec2_t pos) {
    memset(e, 0, sizeof(*e));
    e->id = id;
    e->type = type;
    e->state = ENTITY_STATE_ACTIVE;
    e->position = pos;
}
