# T8.2 evidence — hero/enemy renderers driven by sim state

> [!TIP]
> `SpriteFramesBuilder` groups numbered frames into animations at runtime; HeroRenderer maps sim states (idle/run/attack1-3/smrslt-roll/hurt/die + stance tints) and EnemyRenderer drives the burning-ghoul cycle with hit-flash and stagger slow-mo. Harnesses: `test_hero_render.gd` (hero=true enemy=true) and `test_fight_view.gd` (submitted=true ehp=-144) — approach-then-attack scripted loop reaches `is_fight_over` and emits the verified-shaped claim.
