local wezterm = require 'wezterm'
local config = {}

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

return config

