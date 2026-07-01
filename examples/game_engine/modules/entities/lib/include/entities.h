#ifndef ENTITIES_H
#define ENTITIES_H

#include <engine.h>

typedef struct {
    entity_t base;
    int health;
    int score;
    float speed;
} player_t;

typedef struct {
    entity_t base;
    int health;
    int damage;
    float patrol_radius;
} enemy_t;

typedef struct {
    entity_t base;
    int value;
    int collected;
} item_t;

void player_create(player_t *p, int id, vec2_t pos, float speed);
void player_free(player_t *p);

void enemy_create(enemy_t *e, int id, vec2_t pos, int damage, float radius);
void enemy_free(enemy_t *e);

void item_create(item_t *it, int id, vec2_t pos, int value);
void item_free(item_t *it);

#endif
