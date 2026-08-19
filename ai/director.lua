-- SPDX-License-Identifier: CC-BY-4.0
--
-- director.lua — the shared mission-director library for strike missions (fl-base-pack#3).
--
-- The strike counterpart to instructor.lua's lesson builder, and it exists for the same reason:
-- the mission trigger vocabulary is destroy()/mission_start/timer(), which can end a mission on ONE
-- entity's death but cannot express "the SAM site is down" (three launcher elements), score an
-- objective, or require several target groups. `world.score_objective` + ground-truth queries can,
-- so a strike mission parks an ops vehicle at the field and gives IT a director script built here.
--
-- ⚑ OBJECTIVE SCORING IS THE #1036 STAGE-4 WIRING: each completed group calls
-- `world.score_objective(faction, 1)`, which the match controller turns into points when the server
-- runs a mode with `points_per_objective` (builtin:strike scores a kill 1 and an objective 10).
-- Under the default builtin:free-flight the calls are harmless — the mission still ends on its own
-- success/failure, so the same file serves single-player and a scored coop server.
--
-- ⚠ GROUND TRUTH, DELIBERATELY — same carve-out instructor.lua documents: a director is a test
-- rig/referee, not a pilot. Nothing here flies or senses tactically.

local ins = require('instructor')

local M = {}

--- A target GROUP is dead when no live hostile GROUND unit remains within `radius` metres of its
--- anchor-frame point. The speed gate (< 30 m/s) is what keeps a red CAP overflying the target
--- area from holding an objective hostage — ins.enu distance is horizontal, so without it a
--- fighter passing 4 km overhead would read as "still alive at the depot".
function M.group_dead(self_state, g)
    for _, near in ipairs(nearby_entities(self_state.pos.x, self_state.pos.z, 300000)) do
        local e = get_entity(near.idx)
        if e and not e.dead and e.faction ~= self_state.faction and ins.speed(e) < 30.0 then
            local east, north = ins.enu(e.pos)
            local dx, dz = east - g.point[1], north - g.point[2]
            if math.sqrt(dx * dx + dz * dz) < g.radius then return false end
        end
    end
    return true
end

--- Build a strike director. `cfg.groups` is a list of `{name, point = {east, north}, radius}`;
--- each group that dies scores one objective for the director's own coalition, and the mission
--- succeeds when every group is down. Failure is the clock (`cfg.fail_after_s`) — a strike that
--- cannot run forever; losing the package lead is the mission YAML's `destroy()` trigger to own.
function M.strike(cfg)
    local scored, done, announced = {}, false, false
    return function(self_state, tick, dt)
        if done then return {} end
        if not announced then
            announced = true
            print(string.format("DIRECTOR start: %s (%d groups)", cfg.name or "?", #cfg.groups))
        end
        if world.get_elapsed_time() > (cfg.fail_after_s or 1800) then
            done = true
            print("DIRECTOR fail: out of time")
            world.mission_failure()
            return {}
        end
        -- 1 Hz is plenty for scoring, and never before the spawn wave has settled: a query at
        -- tick 0 that sees no red yet would score every objective and end the mission unflown.
        if tick < 120 or tick % 60 ~= 0 then return {} end

        local n_done = 0
        for _, g in ipairs(cfg.groups) do
            if scored[g.name] then
                n_done = n_done + 1
            elseif M.group_dead(self_state, g) then
                scored[g.name] = true
                n_done = n_done + 1
                print(string.format("DIRECTOR objective complete: %s", g.name))
                world.score_objective(self_state.faction, 1)
            end
        end
        if n_done == #cfg.groups then
            done = true
            print("DIRECTOR complete: " .. (cfg.name or "?"))
            world.set_music_state("success")
            world.mission_success()
        end
        return {}
    end
end

return M
