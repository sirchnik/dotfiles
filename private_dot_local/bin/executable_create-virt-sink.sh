#!/bin/bash

set -e

# Check if "Simultaneous Output" node exists and delete it
existing_node=$(pw-cli ls Node | grep -B 4 'node.name = "Simultaneous Output"' | head -n1 | awk '{print $2}' | tr -d ',')

if [ -n "$existing_node" ]; then
    echo "Deleting existing 'Simultaneous Output' (id=$existing_node)..."
    pw-cli destroy "$existing_node"
fi

# Create a new sink called Simultaneous Output
pw-cli create-node adapter '{ factory.name=support.null-audio-sink node.name="Simultaneous Output" node.description="Simultaneous Output" media.class=Audio/Sink object.linger=true audio.position=[FL FR] }'

# Connect the normal permanent sound card output to the new sink
pw-link "Simultaneous Output:monitor_FL" alsa_output.pci-0000_00_1f.3.analog-stereo:playback_FL
#pw-link "Simultaneous Output:monitor_FR" alsa_output.pci-0000_00_1f.3.analog-stereo:playback_FR
pw-link "Simultaneous Output:monitor_FR" alsa_output.pci-0000_00_1f.3.hdmi-stereo-extra1:playback_FR
pw-link "Simultaneous Output:monitor_FR" alsa_output.pci-0000_00_1f.3.hdmi-stereo:playback_FR

new_node=$(pw-cli ls Node | grep -B 4 'node.name = "Simultaneous Output"' | head -n1 | awk '{print $2}' | tr -d ',')

# Switch the default output to the new virtual sink
wpctl set-default "$new_node"
