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

-- Dictation keys from before Alt + Space and Right Alt became the defaults
-- (added by Omarchy migration 1793477875; Voxtype is the backend here).
if o.dictation_installed and o.dictation_installed() then
  o.bind("SUPER + CTRL + X", "Toggle dictation", "omarchy-dictation toggle")
  o.bind_hold("F9", "Start dictation (push-to-talk)", "omarchy-dictation start", "Stop dictation (push-to-talk)", "omarchy-dictation stop")
end

-- Hex (anomaly.hex): F10 hold to dictate, F8 Annotate (tap to record, hold to draw).
if o.cmd_present("hex") then
  o.bind_hold("F10", "Hex dictation (push-to-talk)", "hex dictation start", "Hex dictation stop", "hex dictation stop")
  o.bind("F8", "Hex Annotate", hl.dsp.global("anomaly.hex:capture"))
end
