-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 4 — IR missile employment (fl-base-pack#15). One AIM-9P shot on a non-manoeuvring target.
--
-- The bandit is a MiG-21bis flown by the pack's own fighter.lua, which will fight back the moment it
-- sees the student — the RP-22 is short-legged and flare-less (entities/mig21bis.toml), so an
-- attacker who arrives from behind and above owns the engagement, and one who blunders in front of
-- it does not. That asymmetry is the lesson.
local ins = require('instructor')

local lesson = ins.lesson({
    name = "IR missile employment",
    fail_after_s = 1200,
    steps = {
        { name = "airborne", done = function(s) return ins.airborne(s) end },
        { name = "bandit destroyed", done = function(s, self)
            -- No survivors near the bandit's spawn (anchor frame, matching the mission YAML) —
            -- the radius is wide because the bandit is the only red air and it moves.
            return ins.live_near(self, { { 14000, 0, 20000 } }, 60000.0) == 0
        end },
    },
})

function compute_control(state, tick, dt) return lesson(state, tick, dt) end
