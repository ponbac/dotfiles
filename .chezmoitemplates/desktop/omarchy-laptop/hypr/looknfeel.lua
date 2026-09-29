-- Change the default Omarchy look'n'feel.

-- Ayaka styling belongs in user config: repo-installed theme Lua is not loaded.
-- Ported from the shared post-Quattro migration workbook.
local active_border_color = "rgba(e65c5cff)"
local inactive_border_color = "rgba(404040ff)"
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
hl.animation({ leaf = "workspaces", enabled = false })
-- Frosted-glass bar: blur the notch, not the transparent strip beside it.
hl.layer_rule({
  match = { namespace = "^omarchy-bar$" },
  blur = true,
  ignore_alpha = 0.1,
})
hl.layer_rule({
  match = { namespace = "^vicinae$" },
  blur = true,
  ignore_alpha = 0,
  no_anim = true,
  animation = "none",
})

-- https://wiki.hypr.land/Configuring/Basics/Variables/#general
-- Omasnap captures before showing its overlay. Excluding this layer from
-- screen sharing would black out scrolling captures, including transparent areas.
hl.layer_rule({
  match = { namespace = "^omasnap$" },
  no_anim = true,
  animation = "none",
})
hl.env("OMARCHY_SCREENSHOT_EDITOR", "omasnap")

-- hl.config({
--   general = {
--     -- No gaps between windows or borders.
--     gaps_in = 0,
--     gaps_out = 0,
--     border_size = 0,
--
--     -- Change to niri-like side-scrolling layout.
--     layout = "scrolling",
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#decoration
-- hl.config({
--   decoration = {
--     -- Use round window corners.
--     rounding = 8,
--
--     -- Dim unfocused windows (0.0 = no dim, 1.0 = fully dimmed).
--     dim_inactive = true,
--     dim_strength = 0.15,
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#animations
-- hl.config({
--   animations = {
--     -- Disable all animations.
--     enabled = false,
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#layout
-- hl.config({
--   layout = {
--     -- Avoid overly wide single-window layouts on wide screens.
--     single_window_aspect_ratio = { 1, 1 },
--   },
-- })

-- https://wiki.hypr.land/Configuring/Layouts/Scrolling-Layout/
-- hl.config({
--   scrolling = {
--     -- See only one column per screen instead of two.
--     column_width = 0.97,
--   },
-- })
