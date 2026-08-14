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
-- EMPLOYMENT (Epic fighters-legacy#583): the AI shoots. The fire surface is three return fields --
-- trigger (level: hold for a gun burst, the server rate-limits), release (edge: one store per
-- press), and weapon_station (absolute hardpoint index). They are INTENTS: the server's fire
-- control re-validates station, ammo, rate and envelope exactly as it does for a player. There is
-- no loadout/ammo/lock query in the Lua API, so station numbers are hardcoded to the entity def's
-- hardpoints (see GUN_STATION / MISSILE_STATION) and "in parameters" is inferred from geometry.
-- The IR AIM-9P is boresight/uncaged, so the missile shot needs only aspect + range, not a radar
-- lock -- its own seeker does the acquiring after launch.
--
-- BVR (fl-base-pack#6): the AIM-7M rides the SHOOTER's radar. There is still no lock COMMAND in
-- the Lua API, but none is needed: a contact whose `state == "locked"` IS the radar track (TWS
-- soft lock), an AI launch designates along the NOSE, and mid-course SARH support only needs that
-- contact held Locked on the shooter's own table (engine #628/#526). So the Sparrow shot is: fire
-- with a locked contact on the nose, then HOLD the nose on it through time of flight -- a support
-- drop coasts the missile seeker's lock_hold_s, then it flies dumb. Because there is no ammo
-- query, an airframe with nothing on the radar-missile station (the F-5E) still enters the
-- support hold after a "launch" that no-opped server-side: it flies pure pursuit instead of lead
-- pursuit for up to the TOF window, which still closes the fight and still employs IR/guns the
-- moment parameters appear. That is the price of honest no-introspection, and it is small.
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
local ALT_LEAD_S   = 5.0                  -- s, altitude-hold anticipation: steer to where the jet
                                          -- WILL be, so the sink rate is arrested before the target
                                          -- altitude, not after (#53 — P-only overshot into the deck)
local MAX_BANK     = 1.05                 -- rad (~60 deg): level-turn cap; no G limiter on this jet
local ROLL_GAIN    = 2.0                  -- aileron per rad of bank error (saturates at ~30 deg off)

-- ── weapon employment (per entities/f5e.toml hardpoints) ─────────────────────────────────────
local GUN_STATION     = 0                  -- slot 0: M39A2 cannon (internal)
local MISSILE_STATION = 1                  -- slot 1: AIM-9P, left wingtip rail
local GUN_RANGE_M     = 900               -- inside this a gun snapshot is worth taking (~0.5 nm)
local GUN_CONE_COS    = 0.9962            -- cos(5 deg): guns want a tight tracking solution
local MSL_RANGE_M     = 9260              -- 5 nm: the seeker's search-lobe reach (aim9p_seeker.toml)
local MSL_MIN_M       = 560               -- ~0.3 nm: inside the missile's own min arming range
local MSL_CONE_COS    = 0.9397            -- cos(20 deg): the uncaged seeker acquisition basket

-- ── BVR employment (fl-base-pack#6). Station 5 = radar missile: the F-16A's mid-wing AIM-7M
-- pair (entities/f16a.toml). On the F-5E slot 5 is an EMPTY bomb station, and a release intent
-- on an empty station is a server no-op, so the shared script stays safe. New defs that follow
-- 0 = gun / 1 = IR missile / 5 = radar missile reuse this script unforked (#41/#43).
local SARH_STATION  = 5
local SARH_RANGE_M  = 28000               -- ~15 nm launch window: inside the aim7m's 20 nm
                                          -- employment reach and the APG-66's 22 nm track lobe
local SARH_MIN_M    = 3500                -- inside this the Sparrow is the wrong tool; save the rail
local SARH_CONE_COS = 0.9659              -- cos(15 deg): AI launch designation is along the NOSE
local SARH_TOF_MPS  = 700                 -- coarse shot closing speed (boost ~M4, then coast) for
                                          -- the support-hold deadline
local SARH_REFIRE_TICKS = 900             -- 15 s between launch attempts. A lock that flickers at
                                          -- the track-lobe edge would otherwise open a fresh fire
                                          -- window every second or two (observed: 33 attempts in
                                          -- one duel) and dump both rails into the first flicker.
local SARH_STEER_AGG = 2.5                -- bank aggressiveness for launch alignment + support:
                                          -- full MAX_BANK from ~24 deg of heading error, so the
                                          -- nose actually converges onto a crossing target
local sarh_support_until = nil            -- tick deadline while supporting a Sparrow in flight
local sarh_target_idx    = nil            -- the supported contact's entity idx
local sarh_last_fire     = -1e9           -- tick of the last launch attempt

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

-- Cosine of the angle off our nose to a world point, and the 3-D range to it. Uses the body +X
-- forward vector so a shot decision respects pitch, not just heading.
local function boresight(state, p)
    local f  = guidance.body_forward(state.quat)
    local dx, dy, dz = p.x - state.pos.x, p.y - state.pos.y, p.z - state.pos.z
    local d  = math.sqrt(dx * dx + dy * dy + dz * dz)
    if d < 1 then return 1.0, 0 end
    return (f.x * dx + f.y * dy + f.z * dz) / d, d
end

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
-- `agg` (optional, default 1) scales the bank the heading error commands. The default P-map
-- reaches MAX_BANK only at 90 deg of error, and a ~40 deg error commands a ~28 deg bank whose
-- turn rate can exactly match a crossing target's bearing drift — a stable pursuit-curve
-- equilibrium that holds the nose off the target forever (observed: herr pinned at 42-50 deg
-- through a whole 14->5 km conversion). The BVR phases pass agg > 1 to break it; every
-- pre-existing call keeps the #53-tuned default.
local function steer(state, tx, tz, talt, throttle, ab, agg)
    local herr = guidance.heading_error(state.quat, state.pos, { x = tx, y = state.pos.y, z = tz })
    -- Close the roll loop on BANK, not on heading (#53). bank_to_turn_aileron maps heading error
    -- straight to aileron, but aileron commands roll RATE on this airframe — fed raw, a sustained
    -- heading error (any orbit is one) integrates the bank past knife-edge and the jet rolls
    -- inverted. Use the helper's shaped/saturated output as the TARGET bank fraction instead,
    -- and fly the aileron to that bank.
    local tbank = clamp(guidance.bank_to_turn_aileron(herr) * MAX_BANK * (agg or 1.0),
                        -MAX_BANK, MAX_BANK)
    local ail   = clamp(ROLL_GAIN * (tbank - bank_of(state)), -1, 1)
    -- NB: pitch_error_from_alt takes (quat, own_pos, alt_error) — own_pos is needed because "up"
    -- is geodetic on a spherical Earth.
    -- PD, not P: feed the helper the error at the PREDICTED altitude (pos.y + lead * climb rate).
    -- The vertical-speed term is the derivative half of the loop — a jet sinking at 100 m/s sees
    -- zero error 500 m above the target and starts its pull there, instead of porpoising through.
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

    -- ── SARH SUPPORT HOLD (fl-base-pack#6). A Sparrow is in the air: keep the illuminating
    -- track alive by holding the nose on the SUPPORTED contact until the time-of-flight window
    -- closes. Support rides this aircraft's own contact table, so the one thing that matters is
    -- that contact staying "locked" -- and the APG-66's 55/25 deg track lobe forgives normal
    -- maneuvering, so flying AT the contact is more than enough pointing. On support loss the
    -- missile coasts its seeker's lock_hold_s and goes dumb; nothing to do then but fight on.
    if sarh_support_until then
        if tick >= sarh_support_until then
            sarh_support_until, sarh_target_idx = nil, nil   -- shot resolved, either way
        else
            local sup = nil
            for _, c in ipairs(detected_contacts()) do
                if c.idx == sarh_target_idx then sup = c break end
            end
            if not (sup and sup.state == "locked") then
                sarh_support_until, sarh_target_idx = nil, nil   -- lock gone; the shot is on its own
            else
                local out = steer(state, sup.pos.x, sup.pos.z,
                                  math.max(sup.pos.y, FLOOR + 200), 1.0, false, SARH_STEER_AGG)
                -- The hold points us at the target anyway -- take the shot if one appears.
                local cosang, rng = boresight(state, sup.pos)
                if cosang >= GUN_CONE_COS and rng <= GUN_RANGE_M then
                    out.weapon_station = GUN_STATION
                    out.trigger        = true
                elseif cosang >= MSL_CONE_COS and rng >= MSL_MIN_M and rng <= MSL_RANGE_M then
                    out.weapon_station = MISSILE_STATION
                    out.release        = true
                end
                return out
            end
        end
    end

    local tgt, dist = pick_target(state)

    if tgt then
        -- Closure speed along the line of sight, from the contact's LAST-KNOWN velocity.
        local dx, dz = tgt.pos.x - state.pos.x, tgt.pos.z - state.pos.z
        local d      = math.max(len2(dx, dz), 1)
        local vc     = ((state.vel.x - tgt.vel.x) * dx + (state.vel.z - tgt.vel.z) * dz) / d

        if dist > ENGAGE_M then
            -- ── EMPLOY, BVR: when a Sparrow shot is AVAILABLE (locked contact, launch window,
            -- rail cooled down), abandon the lead point and put the nose ON the contact — the
            -- launch designator picks the contact along the nose and the support hold wants the
            -- same geometry; the missile pulls its own lead. Lead-pursuit intercept keeps a
            -- standing lead angle on any crossing target (observed ~35 deg through a whole
            -- stern conversion), so gating the shot on nose-on WITHOUT steering nose-on means
            -- the window never opens. Fire on alignment; the release edge means one store.
            local cosang, rng = boresight(state, tgt.pos)
            -- Kinematic launch quality: the Sparrow's 20 nm employment figure is a HEAD-ON
            -- number. Scale the accepted launch range with closure so a tail-chase does not
            -- waste both rails at gate range (observed: two shots at 21 and 18 km on a
            -- receding target, both hopeless): ~35 s of closure contribution over a 9 km
            -- floor, capped at the employment gate.
            local rmax = clamp(9000 + vc * 35, 6000, SARH_RANGE_M)
            if tgt.state == "locked"
               and rng >= SARH_MIN_M and rng <= rmax
               and tick - sarh_last_fire >= SARH_REFIRE_TICKS then
                local out = steer(state, tgt.pos.x, tgt.pos.z,
                                  math.max(tgt.pos.y, FLOOR + 200), 1.0, vc < 120, SARH_STEER_AGG)
                if cosang >= SARH_CONE_COS then
                    out.weapon_station = SARH_STATION
                    out.release        = true
                    sarh_last_fire     = tick
                    sarh_target_idx    = tgt.idx
                    sarh_support_until = tick + math.floor(clamp(rng / SARH_TOF_MPS, 6, 30) * 60)
                end
                return out
            end

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

        -- ── EMPLOY. Geometry decides which weapon; the server's fire control has the final say. ──
        -- Aim at the last-known point (honest sensing: no ground truth even to shoot at).
        local cosang, rng = boresight(state, tgt.pos)
        if cosang >= GUN_CONE_COS and rng <= GUN_RANGE_M then
            out.weapon_station = GUN_STATION
            out.trigger        = true        -- level: the server rate-limits the burst
        elseif cosang >= MSL_CONE_COS and rng >= MSL_MIN_M and rng <= MSL_RANGE_M then
            out.weapon_station = MISSILE_STATION
            out.release        = true        -- edge-detected: exactly one missile off the rail
        end
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
