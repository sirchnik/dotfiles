local wezterm = require 'wezterm'
local config = {}

function get_os()
    return package.config:sub(1,1) == "\\" and "win" or "unix"
end

function scheme_for_appearance(appearance)
  if appearance:find("Dark") then
    return "Builtin Solarized Dark"
  else
    return "Builtin Solarized Light"
  end
end

--config.color_scheme = 'Default (dark) (terminal.sexy)'
config.font =  wezterm.font_with_fallback {'IntoneMono NF', 'Symbols Nerd Font', 'Noto Sans Symbols'}
config.window_background_opacity = 0.9
color_scheme = scheme_for_appearance(wezterm.gui.get_appearance())
config.window_decorations = "RESIZE"
config.check_for_updates = false

if get_os() == "win" then
  config.check_for_updates = true
  config.default_prog = { "nu.exe" }
end

return config

