#!/bin/bash

CONFIG_FILE="$HOME/.config/sink-switcher.conf"

get_sink_from_config() {
  local sink_number=$1
  awk -F '=' -v key="$sink_number" '$1 == key {print $2}' "$CONFIG_FILE"
}

if [[ ! -f $CONFIG_FILE ]]; then
  echo "Error: Configuration file '$CONFIG_FILE' not found."
  exit 1
fi

case $1 in
  1) sink=$(get_sink_from_config "1") ;;
  2) sink=$(get_sink_from_config "2") ;;
  *) sink=$(get_sink_from_config "1") ;;
esac

if [[ -z $sink ]]; then
  echo "Error: Sink not found for the given input."
  exit 1
fi

pactl set-default-sink "$sink"
