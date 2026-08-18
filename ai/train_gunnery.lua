-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 3 — Gunnery (fl-base-pack#15). Strafe a soft convoy with the gun, then recover.
--
-- The targets are Ural-375s: the softest thing in the pack (60 hp) and the reason a student's first
-- air-to-ground pass is not flown into an air-defence site. The mission strips the missiles from the
-- rails with a `loadout:` override, so this lesson is the gun or nothing.
local ins = require('instructor')

local CONVOY = { { 14000, 0, -9000 }, { 14260, 0, -9200 }, { 14520, 0, -9400 } }

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
