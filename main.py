#!/usr/bin/env python3
"""Unified entry point for ChatECNU CLI with platform detection"""

import sys
import os

# Platform detection and handler selection
if sys.platform.startswith('linux'):
    from platform_handlers.linux import linux_input_handler as platform_input_handler
if sys.platform.startswith('win'):
    from platform_handlers.windows import windows_input_handler as platform_input_handler, init_windows_ansi

from chat_session import ChatSession, initialize_openai_client, get_common_parser
from command_processor import CommandProcessor

def main():
    # Get script directory (resolving symlinks for Linux)
    if sys.platform.startswith('linux'):
        script_dir = os.path.dirname(os.path.realpath(__file__))

    # Initialize Windows ANSI color support if running on Windows
    if sys.platform.startswith('win'):
        init_windows_ansi()
        script_dir = os.path.dirname(os.path.abspath(__file__))

    parser = get_common_parser()
    args = parser.parse_args()

    client = initialize_openai_client(script_dir)

    command_processor = CommandProcessor(script_dir)
    session = ChatSession(
        model=args.model,
        temperature=args.temperature,
        system_prompt=args.prompt_file,
        file_paths=args.files,
        image_paths=args.images,
        load_chat_file=args.load_chat,
        script_dir=script_dir,
        command_processor=command_processor
    )

    if args.print:
        session.start(client, lambda: None, non_interactive_input=args.print)
    else:
        session.start(client, platform_input_handler)

if __name__ == "__main__":
    main()
