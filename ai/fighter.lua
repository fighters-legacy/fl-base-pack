-- SPDX-FileCopyrightText: Contributors to fl-base-pack
-- SPDX-License-Identifier: CC-BY-4.0
--
-- fighter.lua — fighter behaviour for the bundled aircraft (fl-base-pack#6).
--
-- HONEST SENSING, BY CONSTRUCTION. This script uses detected_contacts() exclusively — it never
-- calls nearby_entities() or get_entity() for targeting. The AI sees what its sensors give it and
-- nothing else: an F-5E with its short-ranged APQ-159 genuinely hunts by eyeball, a contact that
-- breaks the radar cone goes stale and is eventually dropped, and `reacted` gates everything so
-- reflexes come from the difficulty setting, not from the script.
--
-- WHAT THIS AI DOES NOT DO: shoot. There is no fire path in the engine yet (Epic
-- fighters-legacy#583) — weapons are stores with mass and drag, not ordnance. So "engage" means
-- achieving and holding a guns-quality position behind the target. When #583 lands, the firing
-- decision slots into ENGAGE where marked.
--
-- Tuning note: gains below are deliberately conservative for the F-5E — it has no G limiter
-- (has_fbw = false) and the engine will hand out over-G damage (fighters-legacy#816), so the
-- script must fly within the airframe's limits on its own.

-- ── module state (per entity; lua_State is not shared) ──────────────────────────────────────
local patrol_cx, patrol_cz = nil, nil     -- captured from first tick's position
local PATROL_ALT   = 3000                 -- m
local PATROL_R     = 6000                 -- m, orbit radius
local FLOOR        = 600                  -- m, hard deck: recover below this, always
local STALE_S      = 8.0                  -- s, drop a coasting contact older than this
local ENGAGE_M     = 2500                 -- m, within this: fight for position, not closure

local function len2(x, z) return math.sqrt(x * x + z * z) end

-- Pick the nearest hostile contact the pilot has actually noticed and can still trust.
local function pick_target(state)
    local best, best_d = nil, 1e30
    for _, c in ipairs(detected_contacts()) do
        if c.reacted                                -- reflexes are the difficulty's job, not ours
           and c.faction ~= 0                       -- neutral is not a target
           and c.faction ~= state.faction           -- friendly is not a target
           and c.age_s < STALE_S then               -- a stale coast is a memory, not a contact
            local d = len2(c.pos.x - state.pos.x, c.pos.z - state.pos.z)
            if d < best_d then best, best_d = c, d end
        end
    end
    return best, best_d
end

-- Steer toward a world point at a given altitude; the shared inner loop of every state.
local function steer(state, tx, tz, talt, throttle, ab)
    local herr = guidance.heading_error(state.quat, state.pos, { x = tx, y = state.pos.y, z = tz })
    local ail  = guidance.bank_to_turn_aileron(herr)
    local perr = guidance.pitch_error_from_alt(state.quat, talt - state.pos.y)
    return {
        aileron     = ail,
        rudder      = guidance.coordinated_rudder(ail),
        elevator    = guidance.elevator_from_pitch_error(perr),
        throttle    = throttle,
        afterburner = ab or false,
    }
end

function compute_control(state, tick, dt)
    if not patrol_cx then patrol_cx, patrol_cz = state.pos.x, state.pos.z end

    -- Hard deck first. Terrain does not negotiate, and damaged aircraft (thrust_factor < 1)
    -- sink into it while scripts argue about geometry.
    if state.pos.y < FLOOR then
        local out = steer(state, patrol_cx, patrol_cz, PATROL_ALT, 1.0, true)
        out.elevator = 0.5                      -- firm, not panicked: no G limiter on this jet
        return out
    end

    local tgt, dist = pick_target(state)

    if tgt then
        -- Closure speed along the line of sight, from the contact's LAST-KNOWN velocity.
        local dx, dz = tgt.pos.x - state.pos.x, tgt.pos.z - state.pos.z
        local d      = math.max(len2(dx, dz), 1)
        local vc     = ((state.vel.x - tgt.vel.x) * dx + (state.vel.z - tgt.vel.z) * dz) / d

        if dist > ENGAGE_M then
            -- INTERCEPT: lead pursuit on the last-known state. Aim where it will be, not where
            -- it was — and the older the contact, the less lead we trust.
            local lead = math.min(dist / math.max(vc, 100), 12) * (tgt.age_s < 1 and 1 or 0.4)
            local ax, az = tgt.pos.x + tgt.vel.x * lead, tgt.pos.z + tgt.vel.z * lead
            -- Burner only while we actually need closure; the J85s drink 3x MIL fuel in AB.
            return steer(state, ax, az, math.max(tgt.pos.y, FLOOR + 200), 1.0, vc < 120)
        end

        -- ENGAGE: fight for the rear quarter. Blend pure pursuit with lag pursuit as we close,
        -- so we slide behind the target instead of overshooting through its canopy.
        local lag = math.min((ENGAGE_M - dist) / ENGAGE_M, 0.6)
        local ax  = tgt.pos.x - tgt.vel.x * lag * 2.0
        local az  = tgt.pos.z - tgt.vel.z * lag * 2.0
        local out = steer(state, ax, az, math.max(tgt.pos.y, FLOOR + 200), 1.0, vc < 60)
        -- ── fighters-legacy#583: the firing decision goes here, when weapons can fire. ──
        return out
    end

    -- PATROL: left-hand orbit around the anchor. The sensors do the searching — the radar's
    -- cone sweeps wherever the nose points, which is why the orbit, not the script, finds people.
    local nx, nz = patrol_cx - state.pos.x, patrol_cz - state.pos.z
    local dc = len2(nx, nz)
    if dc > PATROL_R then
        return steer(state, patrol_cx, patrol_cz, PATROL_ALT, 0.75)
    end
    -- tangent point: keep turning around the circle
    nx, nz = nx / math.max(dc, 1), nz / math.max(dc, 1)
    local tx = state.pos.x + nx * math.min(dc, 1500) + nz * 2000
    local tz = state.pos.z + nz * math.min(dc, 1500) - nx * 2000
    return steer(state, tx, tz, PATROL_ALT, 0.7)
end
