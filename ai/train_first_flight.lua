-- SPDX-License-Identifier: CC-BY-4.0
-- Lesson 1 — First Flight (fl-base-pack#15). Take off, climb, come home, land.
-- The syllabus's only lesson with no adversary and no weapon: everything else assumes this one.
local ins = require('instructor')

local lesson = ins.lesson({
    name = "First Flight",
    fail_after_s = 1200,     -- 20 minutes. A first solo is slow; it is not unbounded.
    steps = {
        { name = "airborne",     done = function(s) return ins.airborne(s) end },
        { name = "climb to 3000 m", done = function(s) return s.pos.y > 3000.0 end },
        -- Back overhead the field: the turn for home is the part a student skips.
        { name = "return overhead", done = function(s)
            return ins.within(s, { ins.FIELD_X, 0, ins.FIELD_Z }, 4000.0)
        end },
        { name = "landed",       done = function(s) return ins.landed(s) end },
    },
})

function compute_control(state, tick, dt) return lesson(state, tick, dt) end
