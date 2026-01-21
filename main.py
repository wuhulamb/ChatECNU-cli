"""Unified entry point for ChatECNU CLI with platform detection"""

import sys
import os
import json

from chat import ChatSession
from utils import load_config, initialize_openai_client, get_common_parser, print_conversation, print_error

def main():
    # Get script directory (resolving symlinks for Linux)
    if sys.platform.startswith('linux'):
        script_dir = os.path.dirname(os.path.realpath(__file__))
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load configuration
    config = load_config(script_dir)

    # Platform detection and handler selection
    if sys.platform.startswith('linux'):
        from linux import linux_input_handler as platform_input_handler
    elif sys.platform.startswith('win'):
        from windows import windows_input_handler as platform_input_handler, init_windows_ansi
        # Initialize Windows ANSI color support if running on Windows
        init_windows_ansi()

    parser = get_common_parser()
    args = parser.parse_args()

    # Handle print-chat mode first
    if args.print_chat:
        print_conversation(args.print_chat, config)
        return  # Exit after printing

    if args.model:
        # Parse provider:model format
        if ":" in args.model:
            provider, model = args.model.split(":", 1)
        else:
            # If no provider specified, use default from config
            provider = config.get("default_provider", "ecnu")
            model = args.model
    else:
        provider = config.get("default_provider", "ecnu")
        model = config.get("default_model", "ecnu-max")

    client = initialize_openai_client(script_dir, provider, config)

    session = ChatSession(
        provider=provider,
        model=model,
        temperature=args.temperature,
        system_prompt=args.prompt_file,
        file_paths=args.files,
        image_paths=args.images,
        load_chat_file=args.load_chat,
        script_dir=script_dir,
        config=config  # Pass config directly
    )

    if args.silent:
        session.start(client, lambda: None, non_interactive_input=args.silent)
    else:
        session.start(client, platform_input_handler)

if __name__ == "__main__":
    main()
