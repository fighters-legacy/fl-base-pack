-- SPDX-FileCopyrightText: Contributors to fl-base-pack
-- SPDX-License-Identifier: CC-BY-4.0
--
-- trainer.lua — basic-flight behaviour for the pack's unarmed trainer (the T-38A, fl-base-pack#20).
--
-- WHY A SEPARATE SCRIPT, not fighter.lua. The T-38A carries NO gun, NO missiles and NO hardpoints.
-- fighter.lua employs weapons at hardcoded station indices (GUN_STATION = 0, MISSILE_STATION = 1),
-- and there is no loadout/ammo query in the Lua API, so a shared script CANNOT know at runtime that
-- it is unarmed and skip employment — it would emit fire intents at stations this airframe does not
-- have. Rather than lean on the server to silently no-op those intents, the trainer simply never
-- forms them: "an unarmed aircraft is a first-class citizen" is true here BY CONSTRUCTION. This is
-- basic flight — orbit, navigate, hold altitude, respect the hard deck — the syllabus #15 flies.
--
-- HONEST SENSING, same as fighter.lua. If this script ever grows target-reactive behaviour it must
-- use detected_contacts() exclusively (never nearby_entities()/get_entity()): the trainer sees only
-- what its single day-eyeball sensor gives it. Today it does not target at all — it flies its
-- pattern and lets the sensors do the seeing.
--
-- Tuning note: like the F-5E, the T-38 has no G limiter (has_fbw = false) and the engine hands out
-- over-G damage (fighters-legacy#816), so the gains stay conservative and the script flies within
-- the airframe's own limits.

-- ── module state (per entity; lua_State is not shared) ──────────────────────────────────────
local patrol_cx, patrol_cz = nil, nil     -- captured from first tick's position
local PATROL_ALT   = 3000                 -- m
local PATROL_R     = 6000                 -- m, orbit radius
local FLOOR        = 600                  -- m, hard deck: recover below this, always
local ALT_LEAD_S   = 5.0                  -- s, altitude-hold anticipation: steer to where the jet
                                          -- WILL be, so the sink rate is arrested before the target
                                          -- altitude, not after (#53 — P-only overshot into the deck)
local MAX_BANK     = 1.05                 -- rad (~60 deg): level-turn cap; no G limiter on this jet
local ROLL_GAIN    = 2.0                  -- aileron per rad of bank error (saturates at ~30 deg off)

local function len2(x, z) return math.sqrt(x * x + z * z) end

local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

-- Bank angle about the nose relative to the local horizon; positive = right wing down.
-- quat is {x,y,z,w}; engine body axes are +X fwd, +Y up, +Z right; "up" is the radial from the
-- planet centre {0, -R, 0} (engine flight/Geodetic.h), which is +Y only near the world origin.
local function bank_of(state)
    local q, p = state.quat, state.pos
    local ux, uy, uz = p.x, p.y + 6371000.0, p.z
    local un = math.sqrt(ux * ux + uy * uy + uz * uz)
    ux, uy, uz = ux / un, uy / un, uz / un
    local byx = 2 * (q.x * q.y - q.w * q.z)          -- body-up in world
    local byy = 1 - 2 * (q.x * q.x + q.z * q.z)
    local byz = 2 * (q.y * q.z + q.w * q.x)
    local bzx = 2 * (q.x * q.z + q.w * q.y)          -- body-right in world
    local bzy = 2 * (q.y * q.z - q.w * q.x)
    local bzz = 1 - 2 * (q.x * q.x + q.y * q.y)
    return math.atan(-(ux * bzx + uy * bzy + uz * bzz), ux * byx + uy * byy + uz * byz)
end

-- Steer toward a world point at a given altitude; the shared inner loop of every state.
local function steer(state, tx, tz, talt, throttle, ab)
    local herr = guidance.heading_error(state.quat, state.pos, { x = tx, y = state.pos.y, z = tz })
    -- Close the roll loop on BANK, not on heading (#53). bank_to_turn_aileron maps heading error
    -- straight to aileron, but aileron commands roll RATE on this airframe — fed raw, a sustained
    -- heading error (any orbit is one) integrates the bank past knife-edge and the jet rolls
    -- inverted. Use the helper's shaped/saturated output as the TARGET bank fraction instead,
    -- and fly the aileron to that bank.
    local tbank = guidance.bank_to_turn_aileron(herr) * MAX_BANK
    local ail   = clamp(ROLL_GAIN * (tbank - bank_of(state)), -1, 1)
    -- PD, not P: feed the altitude helper the error at the PREDICTED altitude (pos.y + lead * climb
    -- rate). The vertical-speed term is the derivative half of the loop — a jet sinking at 100 m/s
    -- sees zero error 500 m above the target and starts its pull there, instead of porpoising.
    local aerr = (talt - state.pos.y) - ALT_LEAD_S * state.vel.y
    local perr = guidance.pitch_error_from_alt(state.quat, state.pos, aerr)
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
        local out  = steer(state, patrol_cx, patrol_cz, PATROL_ALT, 1.0, true)
        -- Recover in order: wings, THEN pull. A firm pull while rolled past vertical is a split-S
        -- into the terrain, so level the lift vector first and gate the pull on it pointing up.
        local bank = bank_of(state)
        out.aileron = clamp(-ROLL_GAIN * bank, -1, 1)
        out.rudder  = guidance.coordinated_rudder(out.aileron)
        out.elevator = math.cos(bank) > 0.5 and 0.5 or 0.0   -- firm, not panicked: no G limiter
        return out
    end

    -- PATROL: a left-hand orbit around the anchor at cruise. No targeting and no weapons — this is
    -- an unarmed trainer flying a pattern, not an interceptor. The sensors still see (honest
    -- sensing), but the script never acts on a contact.
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
