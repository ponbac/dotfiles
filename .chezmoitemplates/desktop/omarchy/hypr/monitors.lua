-- Preserve the pre-Quattro fractional scaling for this two-monitor desktop.
hl.env("GDK_SCALE", "1")
hl.monitor({ output = "DP-1", mode = "preferred", position = "auto", scale = 1.066667 })
hl.monitor({ output = "DP-3", mode = "preferred", position = "auto", scale = 1.666667 })
