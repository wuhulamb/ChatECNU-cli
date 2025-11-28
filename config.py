#!/usr/bin/env python3
"""Simplified configuration management for ChatECNU CLI"""

import json
import os
import sys

def print_error(message):
    """Print error message to stderr with proper formatting."""
    print(message, file=sys.stderr)

def load_config(script_dir):
    """Load configuration with simple platform detection."""
    config_path = os.path.join(script_dir, "config.json")

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Simple platform detection
        platform = 'linux' if sys.platform.startswith('linux') else 'windows'

        # Add platform-specific bash config
        config['bash_commands'] = config.get(f'bash_commands_{platform}', {})

        return config

    except FileNotFoundError:
        print_error(f"\033[1;31m[CONFIG] Configuration file not found: {config_path}\033[0m")
        exit(1)
    except json.JSONDecodeError:
        print_error(f"\033[1;31m[CONFIG] Invalid JSON format in config file\033[0m")
        exit(1)
    except Exception as e:
        print_error(f"\033[1;31m[CONFIG] Error loading config: {str(e)}\033[0m")
        exit(1)