local wezterm = require 'wezterm'
local act = wezterm.action
local config = {}

function get_os()
    return package.config:sub(1,1) == "\\" and "win" or "unix"
end

function scheme_for_appearance(appearance)
  if appearance:find 'Dark' then
    return 'Night Owl (Gogh)'
  else
    return 'Night Owlish Light'
  end
end

config.font =  wezterm.font_with_fallback {'IntoneMono NF', 'Symbols Nerd Font', 'Noto Sans Symbols'}
config.window_background_opacity = 0.9
config.color_scheme = 'Night Owl (Gogh)'

wezterm.on('window-config-reloaded', function(window, pane)
  local overrides = window:get_config_overrides() or {}
  local appearance = window:get_appearance()
  local scheme = scheme_for_appearance(appearance)
  if overrides.color_scheme ~= scheme then
    overrides.color_scheme = scheme
    window:set_config_overrides(overrides)
  end
end)
config.window_decorations = "RESIZE"
config.check_for_updates = false
config.enable_scroll_bar = true
min_scroll_bar_height = "1cell"

config.keys = {}
for i = 1, 9 do
  table.insert(config.keys, {
    key = tostring(i),
    mods = 'ALT',
    action = act.ActivateTab(i - 1),
  })
end

local mux = wezterm.mux

wezterm.on('gui-startup', function(cmd)
  local tab, pane, window = mux.spawn_window(cmd or {})
  window:gui_window():maximize()
end)

config.skip_close_confirmation_for_processes_named =  {
	'ssh',
	'nu',
	'carapace',
	'starship',
	'bash',
	'zsh',
	'btop'
}

config.colors = {
  tab_bar = {
    background = "none",
  }
}

return config

