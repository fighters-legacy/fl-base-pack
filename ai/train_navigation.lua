-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 2 — Navigation (fl-base-pack#15). Three legs to three ground landmarks, then home.
--
-- The landmarks are real entities (parked trucks), not invisible coordinates: this pack has no
-- navigation instrument content, so the lesson is flown by looking outside, which is also how it
-- was taught before it was taught any other way.
local ins = require('instructor')

-- Anchor-frame [east, -, north] of the home field, matching the parked landmark trucks in
-- missions/t38a_navigation.yaml — a triangle over the range land north and east of the field,
-- because that is where a training sortie from this field would actually be sent.
local ALPHA = { 22000, 0, 4000 }
local BRAVO = { 14000, 0, 18000 }
local CHARLIE = { -6000, 0, 16000 }

local lesson = ins.lesson({
    name = "Navigation",
    fail_after_s = 1500,
    steps = {
        { name = "airborne",        done = function(s) return ins.airborne(s) end },
        { name = "waypoint alpha",  done = function(s) return ins.within(s, ALPHA, 2500.0) end },
        { name = "waypoint bravo",  done = function(s) return ins.within(s, BRAVO, 2500.0) end },
        { name = "waypoint charlie", done = function(s) return ins.within(s, CHARLIE, 2500.0) end },
        { name = "landed",          done = function(s) return ins.landed(s) end },
    },
})

function compute_control(state, tick, dt) return lesson(state, tick, dt) end
