-- SUPER+F was Quattro's full screen; preserve the pre-Quattro full-width behavior.
hl.unbind("SUPER + F")
o.bind("SUPER + F", "Full width", hl.dsp.window.fullscreen({ mode = "maximized" }))

-- SUPER+ALT+F was Quattro's full width; preserve forced full screen here.
hl.unbind("SUPER + ALT + F")
o.bind("SUPER + ALT + F", "Force full screen", hl.dsp.window.fullscreen({ mode = "fullscreen" }))

o.bind("SUPER + SHIFT + T", "Activity", { tui = "btop" })

-- Move Omarchy's launcher from SUPER+SPACE, replacing the apps-only menu.
hl.unbind("SUPER + SPACE")
hl.unbind("SUPER + ALT + SPACE")
o.bind("SUPER + ALT + SPACE", "Omarchy menu", "omarchy-menu toggle")
o.bind("SUPER + SPACE", "Vicinae", "vicinae toggle")

-- PRINT was Quattro's grim/slurp/Tensaku screenshot pipeline.
hl.unbind("PRINT")
o.bind("PRINT", "Screenshot", "omasnap")

-- Tmux, YouTube, and ChatGPT remain provided by Quattro's defaults.
