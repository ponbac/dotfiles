-- Ayaka look-and-feel. Keep this in user Hyprland config: cloned theme Lua is
-- dropped when Omarchy stages the theme, so ~/.config/omarchy/themes/ayaka/hyprland.lua
-- is not applied.

local active_border_color = "rgba(e65c5cff)"
local inactive_border_color = "rgba(404040ff)"

-- https://wiki.hypr.land/Configuring/Basics/Variables/#general
-- https://wiki.hypr.land/Configuring/Basics/Variables/#decoration
hl.config({
  general = {
    gaps_in = 4,
    gaps_out = 6,

    col = {
      active_border = active_border_color,
      inactive_border = inactive_border_color,
    },
  },

  group = {
    col = {
      border_active = active_border_color,
      border_inactive = inactive_border_color,
    },
  },

  decoration = {
    rounding = 10,

    blur = {
      enabled = true,
      size = 6,
      passes = 3,
      contrast = 1.5,
      brightness = 0.8,
      vibrancy = 0.2,
      vibrancy_darkness = 0.2,
      noise = 0.07,
      ignore_opacity = true,
    },
  },
})

-- Frosted-glass bar: blur only where the notch is drawn, not the clear strip beside it.
hl.layer_rule({
  match = { namespace = "^omarchy-bar$" },
  blur = true,
  ignore_alpha = 0.1,
})

-- Preserve the pre-Quattro Vicinae layer appearance without its open animation.
hl.layer_rule({
  match = { namespace = "^vicinae$" },
  blur = true,
  ignore_alpha = 0,
  no_anim = true,
  animation = "none",
})
