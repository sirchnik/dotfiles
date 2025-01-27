#!/bin/bash

CONFIG_FILE="~/.config/sink-switcher.conf"

get_sink_from_config() {
  local sink_number=$1
  # Use awk to extract the sink value for the given key
  awk -F '=' -v key="$sink_number" '$1 == key {print $2}' "$CONFIG_FILE"
}

# Ensure the configuration file exists
if [[ ! -f $CONFIG_FILE ]]; then
  echo "Error: Configuration file '$CONFIG_FILE' not found."
  exit 1
fi

# Read the sink from the configuration file based on input argument
case $1 in
  1) sink=$(get_sink_from_config "1") ;;
  2) sink=$(get_sink_from_config "2") ;;
  *) sink=$(get_sink_from_config "1") ;;
esac

# Check if the sink was found
if [[ -z $sink ]]; then
  echo "Error: Sink not found for the given input."
  exit 1
fi

# Set the default sink
pactl set-default-sink "$sink"
