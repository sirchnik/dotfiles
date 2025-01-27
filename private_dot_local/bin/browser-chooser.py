#!/usr/bin/env python3

import json
import os
import re
import sys
import subprocess
from urllib.parse import urlparse

def load_config(config_filename='browser_config.json'):
    xdg_config_home = os.getenv('XDG_CONFIG_HOME', os.path.join(os.path.expanduser('~'), '.config'))
    config_path = os.path.join(xdg_config_home, config_filename)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with open(config_path, 'r') as config_file:
        config = json.load(config_file)

    return config

def get_browser_command(url, config):
    browsers = config['browsers']
    url_config = config['urls']

    print(url_config)
    url_config = { (k.replace('.', r'\.').replace('*', r'.*')):v for k,v in url_config.items()}
    print(url_config)
    matches = [(re.match(pattern, url), browser_key) for pattern, browser_key in url_config.items()]
    print(matches)
    matches = [m for m in matches if m[0] is not None]

    matches = sorted(matches, key=lambda e: len(e[0].group(0)), reverse=True)

    if matches:
        browser_key = matches[0][1]
        return browsers[browser_key].format(url=url)

    default_browser = config.get('default_browser')
    if default_browser in browsers:
        return browsers[default_browser].format(url=url)

    raise ValueError('No matching browser for the given URL.')

def main():
    with open("/home/nik/demo.abc", "a") as f:
        f.write(",".join(sys.argv) + "\n") 
    
    url = sys.argv[1]
    try:
        config = load_config()
        command = get_browser_command(url, config)
        subprocess.run(command, shell=True)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

