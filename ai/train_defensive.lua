-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 6 — Defensive manoeuvring (fl-base-pack#15). Be shot at, and come home anyway.
--
-- ⚑ THE ONLY LESSON IN THE SYLLABUS THE STUDENT PASSES BY SURVIVING. The F-5E is sent up against a
-- MiG-29A carrying R-27R1s and R-73Es with the student's own rails EMPTY (a `loadout:` override):
-- there is no winning this by shooting, which is the point. What is being trained is the chaff and
-- flare magazine the F-5E carries (entities/f5e.toml, 30 chaff / 15 flares since #62) and the
-- decision to defend rather than press.
--
-- The bandit's R-27R1 is semi-active, so BREAKING THE LOCK KILLS THE MISSILE — beaming or notching
-- is not flavour here, it is the counter the missile's own `notch_susceptibility` models.
local ins = require('instructor')

local SURVIVE_S = 240.0

local lesson = ins.lesson({
    name = "Defensive manoeuvring",
    fail_after_s = 1500,
    steps = {
        { name = "airborne", done = function(s) return ins.airborne(s) end },
        { name = "survive the engagement", done = function(s)
            return world.get_elapsed_time() > SURVIVE_S + 60.0
        end },
        { name = "landed", done = function(s) return ins.landed(s) end },
    },
})

function compute_control(state, tick, dt) return lesson(state, tick, dt) end
