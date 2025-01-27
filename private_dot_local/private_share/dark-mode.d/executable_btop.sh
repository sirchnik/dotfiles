#!/bin/sh


sed -i 's|^color_theme = .*|color_theme = "Default"|' $HOME/.config/btop/btop.conf
killall -s USR2 btop

