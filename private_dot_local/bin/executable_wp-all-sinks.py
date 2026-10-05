#!/usr/bin/env python3
import subprocess
import sys

def run_cmd(cmd):
    """Run a shell command and return its output."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def get_sinks():
    """Return a list of all sink IDs."""
    output = run_cmd("pactl list short sinks")
    return [line.split()[0] for line in output.splitlines()]

def get_volume(sink):
    """Return the volume of a sink as an integer percent (front-left)."""
    output = run_cmd(f"pactl list sinks")
    # Extract volume for this sink
    sink_block = ""
    capture = False
    for line in output.splitlines():
        if line.startswith(f"Sink #{sink}"):
            capture = True
            sink_block = ""
        if capture:
            sink_block += line + "\n"
            if line.strip() == "":
                break
    for line in sink_block.splitlines():
        if line.strip().startswith("Volume:") and "front-left" in line:
            return int(line.split()[4].strip('%'))
    return 0

def set_volume(sink, vol):
    """Set sink volume, clamped between 0 and 100."""
    vol = max(0, min(100, vol))
    run_cmd(f"pactl set-sink-volume {sink} {vol}%")

def get_mute(sink):
    """Return True if muted, False otherwise."""
    state = run_cmd(f"pactl get-sink-mute {sink}")
    return state.split()[-1] == "yes"

def set_mute(sink, mute):
    """Mute or unmute a sink. `mute` should be True or False."""
    run_cmd(f"pactl set-sink-mute {sink} {1 if mute else 0}")

def toggle_mute():
    sinks = get_sinks()
    if not sinks:
        print("No sinks found")
        sys.exit(1)
    # Toggle based on the first sink's state
    target_state = not get_mute(sinks[0])
    for sink in sinks:
        set_mute(sink, target_state)

def change_volume(delta):
    """Increase or decrease volume by delta (can be negative)."""
    sinks = get_sinks()
    for sink in sinks:
        cur = get_volume(sink)
        new_vol = cur + delta
        set_volume(sink, new_vol)

def set_all_volume(vol):
    """Set all sinks to a specific volume."""
    sinks = get_sinks()
    for sink in sinks:
        set_volume(sink, vol)

def main():
    if len(sys.argv) != 2:
        print("Usage: allsinks.py {mute|+N|-N|N}")
        print("Examples:")
        print("  allsinks.py mute   # toggle mute on all sinks")
        print("  allsinks.py +5     # increase volume by 5%")
        print("  allsinks.py -10    # decrease volume by 10%")
        print("  allsinks.py 50     # set volume to 50%")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "mute":
        toggle_mute()
    elif arg.startswith(('+', '-')):
        try:
            delta = int(arg)
        except ValueError:
            print(f"Invalid volume change: {arg}")
            sys.exit(1)
        change_volume(delta)
    elif arg.isdigit():
        set_all_volume(int(arg))
    else:
        print(f"Invalid argument: {arg}")
        sys.exit(1)

if __name__ == "__main__":
    main()
