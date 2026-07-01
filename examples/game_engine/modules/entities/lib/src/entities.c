#include "entities.h"

static void player_update(entity_t *self, float dt) {
    player_t *p = (player_t *)self;
    self->position.x += p->speed * dt;
}

static void player_on_collision(entity_t *self, entity_t *other) {
    player_t *p = (player_t *)self;
    if (other->type == ENTITY_TYPE_ITEM) {
        item_t *it = (item_t *)other;
        if (!it->collected) {
            p->score += it->value;
            it->collected = 1;
            other->state = ENTITY_STATE_DEAD;
        }
    }
}

void player_create(player_t *p, int id, vec2_t pos, float speed) {
    entity_init(&p->base, id, ENTITY_TYPE_PLAYER, pos);
    p->base.on_update = player_update;
    p->base.on_collision = player_on_collision;
    p->health = 100;
    p->score = 0;
    p->speed = speed;
}

void player_free(player_t *p) {
    p->base.state = ENTITY_STATE_DEAD;
}

static void enemy_update(entity_t *self, float dt) {
    enemy_t *e = (enemy_t *)self;
    self->position.x += e->patrol_radius * dt * 0.1f;
}

void enemy_create(enemy_t *e, int id, vec2_t pos, int damage, float radius) {
    entity_init(&e->base, id, ENTITY_TYPE_ENEMY, pos);
    e->base.on_update = enemy_update;
    e->health = 50;
    e->damage = damage;
    e->patrol_radius = radius;
}

void enemy_free(enemy_t *e) {
    e->base.state = ENTITY_STATE_DEAD;
}

void item_create(item_t *it, int id, vec2_t pos, int value) {
    entity_init(&it->base, id, ENTITY_TYPE_ITEM, pos);
    it->value = value;
    it->collected = 0;
}

void item_free(item_t *it) {
    it->base.state = ENTITY_STATE_DEAD;
}
