-- SPDX-License-Identifier: CC-BY-4.0
--
-- instructor.lua — the shared half of the training syllabus (fl-base-pack#15).
--
-- ⚑ WHY A SCRIPT AT ALL, WHEN MISSIONS HAVE TRIGGERS. The mission YAML trigger vocabulary is
-- `destroy(id)` / `mission_start` / `timer(n)` (docs/modding/missions.md). A syllabus needs to know
-- things none of those can express: that the student got airborne, reached an altitude, found a
-- waypoint, or — the one every flying lesson ends with — LANDED. `world.on_trigger` and ground-truth
-- queries can express all of them, so each lesson is a small state machine driven from here.
--
-- ⚑ WHAT RUNS THIS. Not the student's aircraft: `ai:` is ignored on a player slot, and a lesson must
-- work whether or not a human has joined. Each mission parks an ops vehicle (a Ural-375) beside the
-- field and gives IT the lesson script. The vehicle is real scenery rather than an invisible
-- director, and it is placed clear of the runway and off the training area.
--
-- ⚠ THIS SCRIPT USES GROUND TRUTH DELIBERATELY. `nearby_entities`/`get_entity` see through terrain
-- and cones, which docs/modding/ai.md calls cheating — correctly, for a pilot. An instructor is not
-- a pilot: it is a test rig, and it is exactly the case the docs carve out ("a scripted camera, a
-- test rig"). Nothing here flies anything.

local M = {}

-- ⚑ THE FRAME: every training mission carries `anchor: home` (engine #1211/#1215), so mission
-- coordinates are [metres east, MSL altitude, metres north] of the sandbox home — and the builtin
-- airfield stands AT the anchor (engine SandboxHome.h / BuiltinAirport.h), so the field centre is
-- ENU (0, 0) at a FIXED elevation of 569.6 m, with the 2500 x 45 m runway 090 running along +east
-- (east -1250 .. +1250 at north ~ 0). The Lua API still hands scripts raw world XYZ, where pos.y is
-- NOT altitude (it is about -2,604,000 here) — hence M.alt and M.enu below, which every predicate
-- goes through. Never compare pos.y to an elevation; that was correct only at the old pole origin.
M.HOME_LAT, M.HOME_LON = 36.24917, -114.99611   -- engine SandboxHome.h, degrees
M.FIELD_ELEV = 569.6                            -- m MSL, fixed (not terrain-resolved, engine #486)
M.RUNWAY_HALF_LEN, M.RUNWAY_HALF_WIDTH = 1250.0, 60.0

local EARTH_R = 6371000.0                       -- engine flight/Geodetic.h kEarthRadiusM
local DEG = math.pi / 180.0
local COS_HOME_LAT = math.cos(M.HOME_LAT * DEG)

--- MSL altitude of an entity, metres. The one honest altitude a script can get (engine #1215).
function M.alt(e)
    return guidance.altitude(e.pos)
end

--- ENU offset of a world position from the home anchor: metres east, metres north. Tangent-plane
--- approximation (small-angle in the latitude difference), good to well under 1% across the
--- ~30 km training area — fine for every tolerance in this syllabus, none tighter than 60 m.
function M.enu(pos)
    local g = guidance.geodetic(pos)
    return (g.lon - M.HOME_LON) * DEG * COS_HOME_LAT * EARTH_R,
           (g.lat - M.HOME_LAT) * DEG * EARTH_R
end

local function dist3(a, b)
    local dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end
M.dist3 = dist3

function M.speed(e)
    return math.sqrt(e.vel.x * e.vel.x + e.vel.y * e.vel.y + e.vel.z * e.vel.z)
end

--- The student. Prefers a player-owned entity; failing that, **the fastest live friendly that is not
--- the instructor** — which in a headless probe is the aircraft, because everything else on the
--- student's side is parked scenery.
---
--- ⚠ "any friendly that is not me" WAS the rule here and it was wrong: the navigation lesson parks
--- three friendly trucks as landmarks, the instructor adopted the first one as its student, and the
--- lesson then waited forever for a truck to get airborne. It reported a clean, healthy, entirely
--- inert mission.
---
--- ⚠ AND "the FASTEST friendly" WAS ALSO WRONG, for a subtler reason: at tick 0 nothing has moved
--- yet, so the aircraft's `speed:` has not reached its velocity and every candidate ties at zero —
--- the scan then adopted whichever the spatial query happened to return first, which was a truck
--- again. So an unowned candidate must be *actually flying* (30 m/s) before the instructor will
--- adopt it, and until then the scan simply comes back empty and runs again. A human student is
--- exempt: `player_owned` wins instantly, parked on the ramp at zero knots, which is exactly where
--- a real lesson begins.
---
--- ⚑ CACHED, AND DELIBERATELY SO. The search is a 200 km ground-truth query plus a `get_entity` per
--- hit; running it every tick for the whole mission would be the most expensive thing in the pack by
--- a wide margin, for an answer that changes at most twice (when a pilot joins, and if they die).
--- So it resolves an index once, reuses it, and only re-scans when the cached entity is gone —
--- at most twice a second.
local cached_idx, next_scan_tick = nil, 0

function M.student(self_state, tick)
    if cached_idx then
        local e = get_entity(cached_idx)
        if e and not e.dead then return e end
        cached_idx = nil
    end
    if tick and tick < next_scan_tick then return nil end
    next_scan_tick = (tick or 0) + 30

    local best_idx, best_speed = nil, -1.0
    for _, near in ipairs(nearby_entities(self_state.pos.x, self_state.pos.z, 200000)) do
        local e = get_entity(near.idx)
        if e and not e.dead and e.faction == self_state.faction
            and dist3(e.pos, self_state.pos) > 5.0 then   -- 5 m: anything closer is me
            if e.player_owned then
                cached_idx = near.idx
                return e
            end
            local sp = M.speed(e)
            if sp > 30.0 and sp > best_speed then best_idx, best_speed = near.idx, sp end
        end
    end
    cached_idx = best_idx
    return best_idx and get_entity(best_idx) or nil
end

function M.airborne(e)
    return M.alt(e) > M.FIELD_ELEV + 120.0 and M.speed(e) > 60.0
end

--- On the deck, slow, and over the runway. All three matter: "low and slow" alone is also what a
--- crash looks like a second before it stops being one, and "on the runway" alone is a taxiing jet.
--- The runway runs ALONG +EAST from the field centre (heading 090), so the length tolerance is the
--- east axis and the width tolerance is north — swapped from the old pole-origin field, where the
--- strip happened to lie along world Z.
function M.landed(e)
    if M.alt(e) >= M.FIELD_ELEV + 12.0 or M.speed(e) >= 25.0 then return false end
    local east, north = M.enu(e.pos)
    return math.abs(east) < M.RUNWAY_HALF_LEN
        and math.abs(north) < M.RUNWAY_HALF_WIDTH
end

--- Inside `radius_m` of an anchor-frame point `{east, alt, north}` (the same numbers the mission
--- YAML uses), horizontally — altitude does not count, a waypoint is a place, not a height.
function M.within(e, point, radius_m)
    local east, north = M.enu(e.pos)
    local dx, dz = east - point[1], north - point[3]
    return math.sqrt(dx * dx + dz * dz) < radius_m
end

--- Count live hostiles standing near a list of anchor-frame points — how a gunnery lesson knows the
--- range is cold without a `destroy()` trigger per target (triggers can only end a mission, not
--- score one). One ground-truth query around the instructor, then the precise check in ENU: the
--- world-XZ shadow of a ground distance shrinks with direction at this latitude, so the query
--- radius is generous and the real test is the per-point ENU distance.
function M.live_near(self_state, points, radius_m)
    local hostiles = {}
    for _, near in ipairs(nearby_entities(self_state.pos.x, self_state.pos.z, 300000)) do
        local e = get_entity(near.idx)
        if e and not e.dead and e.faction ~= self_state.faction then
            local east, north = M.enu(e.pos)
            hostiles[#hostiles + 1] = { east = east, north = north }
        end
    end
    local live = 0
    for _, p in ipairs(points) do
        for _, h in ipairs(hostiles) do
            local dx, dz = h.east - p[1], h.north - p[3]
            if math.sqrt(dx * dx + dz * dz) < radius_m then
                live = live + 1
                break
            end
        end
    end
    return live
end

--- Build a lesson. `cfg.steps` is an ordered list of `{name, done(student, self)}`; each completed
--- step scores one objective for the student's coalition, and the last one ends the mission.
---
--- Failure is explicit and bounded: the student dying, or `cfg.fail_after_s` elapsing. A lesson that
--- can only ever succeed is not a test, and a lesson with no clock hangs a headless run forever.
function M.lesson(cfg)
    local step, done_all, announced = 1, false, false
    return function(self_state, tick, dt)
        if done_all then return {} end
        if not announced then
            announced = true
            print(string.format("LESSON start: %s (%d steps)", cfg.name or "?", #cfg.steps))
        end

        if world.get_elapsed_time() > (cfg.fail_after_s or 1200) then
            print(string.format("LESSON fail: out of time at step %d (%s)", step,
                                cfg.steps[step] and cfg.steps[step].name or "-"))
            done_all = true
            world.mission_failure()
            return {}
        end

        local s = M.student(self_state, tick)
        if not s then return {} end          -- nobody has joined yet: wait, do not fail
        if s.dead then
            done_all = true
            world.mission_failure()
            return {}
        end

        local cur = cfg.steps[step]
        if cur and cur.done(s, self_state) then
            print(string.format("LESSON step %d/%d complete: %s", step, #cfg.steps, cur.name))
            world.score_objective(s.faction, 1)
            step = step + 1
            if step > #cfg.steps then
                done_all = true
                print("LESSON complete: " .. (cfg.name or "?"))
                world.set_music_state("success")
                world.mission_success()
            end
        end
        return {}
    end
end

return M
