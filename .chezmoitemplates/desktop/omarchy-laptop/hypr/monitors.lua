-- See https://wiki.hypr.land/Configuring/Basics/Monitors/
-- List current monitors and supported resolutions with: hyprctl monitors all

local omarchy_gdk_scale = 2
local omarchy_monitor_scale = "auto"

hl.env("GDK_SCALE", tostring(omarchy_gdk_scale))
hl.monitor({ output = "", mode = "preferred", position = "auto", scale = omarchy_monitor_scale })

-- Keep the native lid handling and manual laptop-display toggle.
hl.monitor({ output = "eDP-1", mode = "2560x1600@120", position = "0x0", scale = 2 })

-- Match by model: USB-C dock connector names can change on reconnect.
-- Automatic directions keep the layout contiguous when the laptop panel is off.
hl.monitor({ output = "desc:Dell Inc. DELL U2717D", mode = "preferred", position = "auto-left", scale = 1 })
hl.monitor({ output = "desc:Dell Inc. DELL P2723QE", mode = "preferred", position = "auto-right", scale = 1.5 })

-- Configure a specific monitor.
-- hl.monitor({ output = "DP-2", mode = "2560x1440@144", position = "0x0", scale = 1 })

-- Portrait/rotated secondary monitor (transform: 1 = 90°, 3 = 270°).
-- hl.monitor({ output = "DP-2", mode = "preferred", position = "auto", scale = 1, transform = 1 })
