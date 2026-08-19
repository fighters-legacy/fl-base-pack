-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 5 — Radar missile employment (fl-base-pack#15). The AIM-7M, head-on, from the F-16A.
--
-- This is the lesson #15 could not have until the F-16A and #23 existed: the F-5E's APQ-159 is a
-- ranging set for gun and IR work and cannot support a semi-active shot at all. The adversary is the
-- MiG-29A, which is the pack's only aircraft that can shoot BACK at this range — so the lesson is
-- not "press the button", it is "shoot first and support the missile", because a SARH round flies
-- only while the shooter holds the lock (weapons/aim7m.toml).
local ins = require('instructor')

local lesson = ins.lesson({
    name = "Radar missile employment",
    fail_after_s = 900,
    steps = {
        { name = "airborne", done = function(s) return ins.airborne(s) end },
        { name = "bandit destroyed", done = function(s, self)
            -- Anchor frame, matching the mission YAML; wide because the bandit is the only red air.
            return ins.live_near(self, { { 30000, 0, 0 } }, 80000.0) == 0
        end },
    },
})

function compute_control(state, tick, dt) return lesson(state, tick, dt) end
