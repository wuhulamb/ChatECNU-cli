#!/usr/bin/env python3
"""Linux version of ECNU Chat Client with platform-specific input handling"""

import readline
import os
import sys

from chat_session import ChatSession, initialize_openai_client, get_common_parser

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
            if len(lines) == 1 and line.strip() in ['exit', 'quit', 'save', 'q', 's']:
                break
            elif line.strip() in ['clear', 'c']:
                lines = []
                print("\033[1;36mInput cleared\033[0m")
                break

        return "\n".join(lines).strip()
    except KeyboardInterrupt:
        print("\033[1;36mSession terminated by Ctrl+C\033[0m")
        sys.exit(0)

def linux_main():
    """Linux-specific main function with readline support"""
    # Parse command line arguments
    parser = get_common_parser()
    args = parser.parse_args()

    # Get script directory (resolving symlinks for Linux)
    script_path = os.path.realpath(__file__)
    script_dir = os.path.dirname(script_path)

    # Initialize OpenAI client
    client = initialize_openai_client(script_dir)

    # Create chat session
    session = ChatSession(
        model=args.model,
        temperature=args.temperature,
        system_prompt=args.prompt_file,
        file_paths=args.files,
        image_paths=args.images,
        load_chat_file=args.load_chat,
        script_dir=script_dir
    )

    # Start session with Linux-specific input handler
    session.start(client, linux_input_handler)

if __name__ == "__main__":
    linux_main()
