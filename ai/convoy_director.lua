-- SPDX-License-Identifier: CC-BY-4.0
-- Director for ia_gun_run.yaml (fl-base-pack#3). One objective: the convoy. The Shilka escort is
-- deliberately NOT an objective — killing it is the smart first move, not the mission.
local director = require('director')

local run = director.strike({
    name = "Gun Run",
    fail_after_s = 840,      -- under the mission's timer(900) backstop
    groups = {
        -- 500 m covers all three trucks; the escort sits ~600 m back down the run-in, outside it.
        { name = "convoy destroyed", point = { 12200, 10260 }, radius = 500.0 },
    },
})

function compute_control(state, tick, dt) return run(state, tick, dt) end
