-- SPDX-License-Identifier: CC-BY-4.0
-- Director for coop_strike.yaml (fl-base-pack#3). Three scored objectives; the points must agree
-- with the red object positions in the mission file — they are the same coordinates.
local director = require('director')

local run = director.strike({
    name = "Depot Strike",
    fail_after_s = 1740,     -- under the mission's timer(1800) backstop, so the director reports
    groups = {
        -- The SA-6 battery: the strike is flyable without killing it, but it is worth a point and
        -- it makes the depot run survivable. 500 m covers the battery alone.
        { name = "sam site down",  point = { 27000, 21500 }, radius = 500.0 },
        -- The Shilka parked at the depot fence — the run-in gun.
        { name = "flak down",      point = { 29600, 23700 }, radius = 250.0 },
        -- The strike target. 350 m is the depot alone: the two trucks are parked outside it on
        -- purpose, targets of opportunity rather than objective gates.
        { name = "depot destroyed", point = { 30000, 24000 }, radius = 350.0 },
    },
})

function compute_control(state, tick, dt) return run(state, tick, dt) end
