-- SPDX-FileCopyrightText: Contributors to fl-base-pack
-- SPDX-License-Identifier: CC-BY-4.0
--
-- bomber.lua — route and formation behaviour for the pack's bomber (the B-1B, fl-base-pack#66).
--
-- This is the second half of fl-base-pack#6, whose acceptance is "formation hold, waypoint
-- following, minimal manoeuvring". The fighter half shipped long ago; this half waited because the
-- pack had no bomber to host it, which is the reason the B-1B was chosen.
--
-- WHY A SEPARATE SCRIPT, not fighter.lua. Same argument trainer.lua makes, and stronger. fighter.lua
-- employs weapons at hardcoded station indices (gun 0, IR missile 1, radar missile 5) and there is
-- still no loadout query in the Lua API, so a shared script cannot discover at runtime that it is
-- flying an aircraft whose stations 0-2 are BOMB BAYS. It would form air-to-air fire intents at a
-- bay full of Mk 82s. This script never forms them.
--
-- MINIMAL MANOEUVRING IS A HARD CONSTRAINT HERE, not a style choice. The B-1B is authored at
-- max_g_structural = 2.5 with has_fbw = false, so there is NO limiter between this script and
-- over-G damage (fighters-legacy#816). Every gain below is sized for that: the bank ceiling is 35
-- degrees, which costs 1.22 g in a level turn, against a fighter script's 60 degrees and 2 g.
--
-- CONTROL LAW: bank-closed roll and coordinated rudder come from the guidance primitives added in
-- fighters-legacy#1147 (turn_aileron, sideslip/rudder_to_coordinate), which is what new code should
-- use -- bank_to_turn_aileron commands roll RATE, and fed raw on a sustained turn it rolls the
-- aircraft inverted, exactly as it did to every engine station-keeping controller before #1147.
--
-- ⚠ THE PITCH AXIS IS THE EXCEPTION, and it was measured rather than assumed.
-- `guidance.elevator_for_altitude_hold` holds altitude through a BOUNDED angle of attack, and those
-- bounds are sized for a fighter. This aircraft's pitch inertia is 1.06e7 kg m^2 -- around 150x an
-- F-5E's -- so it responds to a given elevator far more slowly, and the primitive's clamped output
-- never builds the pitch rate needed. Probed headless: spawned level and trimmed at 8000 m, the
-- primitive commanded a steady 0.10 elevator while the sink rate grew monotonically from -15 to
-- -233 m/s, and the aircraft flew into the ground every time.
--
-- So pitch uses the older explicit loop trainer.lua carries, with a lead sized for this airframe
-- (18 s against the trainer's 5). Same probe, same conditions: it holds level flight for the full
-- 18,000-tick run. If the primitive ever learns about airframe inertia, delete this and use it.
--
-- OBSERVED BEHAVIOUR, from the same headless probe (spawned at 8000 m, 207 t, speed 240 m/s, 300 s):
-- the aircraft flies its route through all four waypoints at 275-305 m/s, sinks to about 4200 m,
-- then climbs back through 5000 m and is still climbing when the run ends. It does NOT hold 8000 m
-- promptly, and that is the aeroplane rather than the loop: at 207 t -- essentially maximum takeoff
-- weight, three full bomb bays and full fuel -- sustaining that altitude costs more thrust than a
-- cruise setting gives, so it trades altitude for speed and climbs back as the throttle term winds
-- in. A lighter aircraft, or a mission that wants high-altitude cruise from the start, should spawn
-- it there with `speed:` set; a bomber that snapped to its commanded altitude at max weight would
-- be the suspicious result, not this one.
--
-- HONEST SENSING. Formation lead is found through detected_contacts() only -- never
-- nearby_entities() or get_entity(). A bomber that magically knows where its flight lead is would
-- be cheating in the one place this pack is careful not to (Epic #670).

-- ── tuning (per entity; lua_State is not shared) ─────────────────────────────────────────────
local CRUISE_ALT   = 8000      -- m, route altitude
local FLOOR        = 900       -- m, hard deck: recover below this, always. Higher than the
                               -- trainer's 600 -- this aircraft is 44.5 m long and rolls slowly.
local MAX_BANK     = 0.61      -- rad (35 deg): 1.22 g level. The airframe breaks at 2.5.
local LEG          = 25000     -- m, route leg length
local WP_CAPTURE   = 2500      -- m, waypoint arrival radius: wide, because this aircraft
                               -- cannot pivot around a tight one
local FORM_ASTERN  = 900       -- m, formation station: behind the lead
local FORM_SIDE    = 450       -- m, and offset to the right
local FORM_MIN     = 250       -- m, never close inside this on the lead
local CRUISE_THR   = 0.72
local CLOSE_THR    = 0.92      -- catching up to a formation lead
local ALT_LEAD_S   = 18.0      -- s, altitude-hold anticipation. The trainer uses 5; this aircraft
                               -- is two orders of magnitude heavier in pitch inertia and needs to
                               -- start arresting a sink far earlier (see the control-law note).
local ALT_THR_GAIN = 0.00012   -- throttle per metre of altitude deficit. Without it the aircraft
                               -- settles wherever thrust happens to equal drag -- in the probe,
                               -- 3500 m below its commanded cruise -- because holding 8000 m at
                               -- 207 t simply costs more than 72% throttle.

-- Route state, captured on the first tick from wherever the aircraft was spawned. A mission that
-- wants a specific track should place the aircraft on it; this gives a sane default rather than
-- demanding route data the Lua API has no way to receive yet.
local wp = nil        -- { {x=,z=}, ... }
local wp_i = 1

local function len2(x, z) return math.sqrt(x * x + z * z) end
local function clamp(v, lo, hi) return math.max(lo, math.min(hi, v)) end

-- A closed four-leg racetrack from the spawn point, aligned with the initial heading. Closed so the
-- aircraft never runs off the end of its own route and starts orbiting a corner.
local function build_route(state)
    local q = state.quat
    -- Body +X (nose) in world, flattened to the horizontal plane.
    local fx = 1 - 2 * (q.y * q.y + q.z * q.z)
    local fz = 2 * (q.x * q.y + q.w * q.z)
    local n = math.max(len2(fx, fz), 1e-6)
    fx, fz = fx / n, fz / n
    local rx, rz = -fz, fx                     -- 90 deg right of the nose
    local p = state.pos
    return {
        { x = p.x + fx * LEG,            z = p.z + fz * LEG },
        { x = p.x + fx * LEG + rx * LEG, z = p.z + fz * LEG + rz * LEG },
        { x = p.x + rx * LEG,            z = p.z + rz * LEG },
        { x = p.x,                       z = p.z },
    }
end

-- The shared inner loop. Bank-closed turn, coordinated rudder, altitude-holding elevator.
local function steer(state, tx, tz, talt, throttle)
    local herr = guidance.heading_error(state.quat, state.pos, { x = tx, y = state.pos.y, z = tz })
    -- PD on altitude, not P: feed the helper the error at the PREDICTED altitude, so the sink is
    -- arrested BEFORE the target rather than porpoising through it. See the control-law note.
    local aerr = (talt - state.pos.y) - ALT_LEAD_S * state.vel.y
    local perr = guidance.pitch_error_from_alt(state.quat, state.pos, aerr)
    -- Elevator alone cannot hold a cruise altitude a bomber is too heavy to sustain at part power,
    -- so the deficit buys throttle as well as pitch.
    local thr = clamp(throttle + ALT_THR_GAIN * math.max(0, talt - state.pos.y), 0, 1)
    return {
        -- MAX_BANK is passed explicitly: the primitive defaults to 45 deg, which is more than this
        -- airframe should be asked for at weight.
        aileron     = guidance.turn_aileron(state.quat, state.pos, herr, nil, MAX_BANK),
        rudder      = guidance.rudder_to_coordinate(guidance.sideslip(state.quat, state.vel)),
        elevator    = guidance.elevator_from_pitch_error(perr),
        throttle    = thr,
        afterburner = false,   -- a bomber cruises; burner is for the recovery case below
    }
end

-- The nearest FRIENDLY contact ahead, or nil. Honest sensing: this is whatever the sensors give.
local function formation_lead(state)
    local best, best_d = nil, math.huge
    for _, c in ipairs(detected_contacts()) do
        if c.faction ~= 0 and c.faction == state.faction then
            local d = len2(c.pos.x - state.pos.x, c.pos.z - state.pos.z)
            if d < best_d and d > FORM_MIN then best, best_d = c, d end
        end
    end
    return best, best_d
end

function compute_control(state, tick, dt)
    if not wp then wp = build_route(state) end

    -- Hard deck first. Terrain does not negotiate, and a damaged bomber (thrust_factor down to 0.40
    -- at critical) sinks into it while a script argues about geometry.
    if state.pos.y < FLOOR then
        local out = steer(state, state.pos.x, state.pos.z, CRUISE_ALT, 1.0)
        out.afterburner = true
        return out
    end

    -- FORMATION HOLD, when there is someone to hold on. Station is astern and to the right of the
    -- lead, computed in the lead's frame from its own position -- the script has no access to the
    -- lead's heading through detected_contacts(), so the offset is taken along the bearing from us
    -- to it, which converges to a trail position rather than a precise echelon. That is the honest
    -- limit of what the sensor picture supports, and it is enough for "formation hold".
    local lead, d = formation_lead(state)
    if lead then
        local bx, bz = lead.pos.x - state.pos.x, lead.pos.z - state.pos.z
        local n = math.max(len2(bx, bz), 1e-6)
        bx, bz = bx / n, bz / n
        local station_x = lead.pos.x - bx * FORM_ASTERN - bz * FORM_SIDE
        local station_z = lead.pos.z - bz * FORM_ASTERN + bx * FORM_SIDE
        local thr = d > (FORM_ASTERN * 2) and CLOSE_THR or CRUISE_THR
        return steer(state, station_x, station_z, lead.pos.y, thr)
    end

    -- WAYPOINT FOLLOWING. Advance on capture radius, wrapping at the end of the closed route.
    local t = wp[wp_i]
    if len2(t.x - state.pos.x, t.z - state.pos.z) < WP_CAPTURE then
        wp_i = wp_i % #wp + 1
        t = wp[wp_i]
    end
    return steer(state, t.x, t.z, CRUISE_ALT, CRUISE_THR)
end
