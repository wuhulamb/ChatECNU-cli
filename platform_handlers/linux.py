"""Linux-specific input handling"""

import readline
import sys

def linux_input_handler(input_prompt="(Input text then press Ctrl+D to submit)"):
    """Linux-specific input handler with readline and Ctrl+D support"""
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
            if line.strip() in ['c']:
                lines = []
                print("\033[1;36mInput cleared\033[0m")
                break

        return "\n".join(lines).strip()
    except KeyboardInterrupt:
        print("\033[1;36mSession terminated by Ctrl+C\033[0m")
        sys.exit(0)
