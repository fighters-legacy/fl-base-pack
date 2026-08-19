-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 3 — Gunnery (fl-base-pack#15). Strafe a soft convoy with the gun, then recover.
--
-- The targets are Ural-375s: the softest thing in the pack (60 hp) and the reason a student's first
-- air-to-ground pass is not flown into an air-defence site. The mission strips the missiles from the
-- rails with a `loadout:` override, so this lesson is the gun or nothing.
local ins = require('instructor')

-- Anchor-frame [east, -, north], matching the target trucks in missions/f5e_gunnery.yaml:
-- 13.5 km out on the range land north-east of the field.
local CONVOY = { { 9000, 0, 10000 }, { 9200, 0, 10260 }, { 9400, 0, 10520 } }

local lesson = ins.lesson({
    name = "Gunnery",
    fail_after_s = 1500,
    steps = {
        { name = "airborne", done = function(s) return ins.airborne(s) end },
        { name = "convoy destroyed", done = function(s, self)
            return ins.live_near(self, CONVOY, 400.0) == 0
        end },
        { name = "landed", done = function(s) return ins.landed(s) end },
    },
})

function compute_control(state, tick, dt) return lesson(state, tick, dt) end
