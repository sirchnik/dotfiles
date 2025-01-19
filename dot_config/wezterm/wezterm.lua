local wezterm = require 'wezterm'
local act = wezterm.action
local config = {}

function get_os()
    return package.config:sub(1,1) == "\\" and "win" or "unix"
end

function get_appearance()
  if wezterm.gui then
    return wezterm.gui.get_appearance()
  end
  return 'Dark'
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
config.color_scheme = scheme_for_appearance(get_appearance())
config.window_decorations = "RESIZE"
config.check_for_updates = false
config.enable_scroll_bar = true

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

