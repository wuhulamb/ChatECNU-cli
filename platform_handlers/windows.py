"""Windows-specific input handling"""

import ctypes
import os
import sys

def windows_input_handler(input_prompt="(Input text then press Ctrl+Z + Enter to submit)"):
    """Windows-specific input handler with Ctrl+Z support"""
    try:
        lines = []
        print(f"\n\033[1;32mUser: {input_prompt}\033[0m\n")

        while True:
            try:
                line = input()
            except EOFError:
                break
            except KeyboardInterrupt:
                print("\033[1;36mSession terminated by Ctrl+C\033[0m")
                sys.exit(0)

            lines.append(line)
            if len(lines) == 1:
                if line.strip() in ['q', 's', 'bash on', 'bash off'] or line.strip().startswith('!'):
                    break
            elif line.strip() in ['c']:
                lines = []
                print("\033[1;36mInput cleared\033[0m")
                break

        return "\n".join(lines).strip()
    except KeyboardInterrupt:
        print("\033[1;36mSession terminated by Ctrl+C\033[0m")
        sys.exit(0)

def init_windows_ansi():
    """Initialize ANSI color support on Windows"""
    if os.name == 'nt':
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
