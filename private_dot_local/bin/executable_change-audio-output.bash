#!/bin/bash
sink1=alsa_output.pci-0000_00_1f.3.analog-stereo
sink2=alsa_output.usb-Logitech_Zone_Vibe_125_2342MH00AGR8-00.analog-stereo

case $1 in
  1) pactl set-default-sink $sink1 ;;
  2) pactl set-default-sink $sink2 ;;
  *) pactl set-default-sink $sink1 ;;
esac
