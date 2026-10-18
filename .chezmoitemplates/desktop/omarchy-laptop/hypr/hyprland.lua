-- Learn how to configure Hyprland: https://wiki.hypr.land/Configuring/Start/

-- Omarchy's bootstrap keeps path setup out of this user config.
dofile((os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/default/hypr/bootstrap.lua")

-- Disable all Omarchy default bindings. Add your own in hypr/bindings.lua.
-- omarchy_default_bindings = false
--
-- Or disable only bindings for Omarchy's preinstalled apps/web apps while
-- keeping core window-manager bindings:
-- omarchy_preinstalled_bindings = false

-- Load Omarchy defaults.
require("default.hypr.omarchy")

-- Put your personal overrides in these files. They're loaded after Omarchy's
-- defaults so package updates can improve the defaults without rewriting your
-- ~/.config/hypr files.
require("hypr.monitors")
require("hypr.input")
require("hypr.bindings")
require("hypr.looknfeel")
require("hypr.autostart")

-- Toggle config flags dynamically.
require("default.hypr.toggles")

-- Add any other personal Hyprland configuration below.
-- o.window("qemu", { workspace = "5" })

-- Prefer our Helium web-app launcher after Omarchy sets up its own PATH.
local webapp_override_bin = os.getenv("HOME") .. "/.local/share/omarchy-overrides/bin"
local webapp_path = { webapp_override_bin }
for entry in (os.getenv("PATH") or "/usr/local/bin:/usr/bin"):gmatch("[^:]+") do
  if entry ~= webapp_override_bin then table.insert(webapp_path, entry) end
end
hl.env("PATH", table.concat(webapp_path, ":"))

-- GTK 4.24's empty blur region disables Hyprland 0.56's compositor blur.
-- Keep compositor-controlled blur until upstream fixes omacom/omarchy#15793.
hl.env("GDK_WAYLAND_DISABLE", "ext_background_effect_manager_v1")

-- Keep Helium from stealing focus (and the cursor warp that follows) when
-- agent-browser activates tabs over CDP.
o.window("helium", { focus_on_activate = false })
