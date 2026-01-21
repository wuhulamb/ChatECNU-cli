"""
ChatECNU CLI - Utilities Module
Contains utility functions for file processing, command handling, and other helper functions.
"""

import argparse
import base64
import datetime
import json
import os
import re
import subprocess
import sys

from dotenv import load_dotenv
from openai import OpenAI


def print_error(message):
    """Print error message to stderr with proper formatting."""
    print(message, file=sys.stderr)


# ========== File/Image Processing Functions ==========

def add_file_contents(file_paths, messages):
    """Add multiple file contents to conversation context"""
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print_error(f"\033[1;31m[FILE] File not found: {file_path}\033[0m")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            if not file_content.strip():
                print_error(f"\033[1;31m[WARNING] Empty file: {file_path}\033[0m")
                continue

            messages.append({
                "role": "user",
                "content": f"User has uploaded a file '{file_path}'. Here is its content:\n{file_content}"
            })
        except UnicodeDecodeError:
            print_error(f"\033[1;31m[FILE] Not a UTF-8 encoded file: {file_path}\033[0m")
            return False
        except PermissionError:
            print_error(f"\033[1;31m[FILE] Permission denied: {file_path}\033[0m")
            return False
        except Exception as e:
            print_error(f"\033[1;31m[FILE] Error reading file {file_path}: {str(e)}\033[0m")
            return False

    return True


def add_image_contents(image_paths, messages):
    """Add multiple image contents to conversation context"""
    for image_path in image_paths:
        if not os.path.exists(image_path):
            print_error(f"\033[1;31m[IMAGE] File not found: {image_path}\033[0m")
            return False

        try:
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')

            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": f"User has uploaded an image '{image_path}', please remember its content."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            })

        except PermissionError:
            print_error(f"\033[1;31m[IMAGE] Permission denied: {image_path}\033[0m")
            return False
        except Exception as e:
            print_error(f"\033[1;31m[IMAGE] Error processing image {image_path}: {str(e)}\033[0m")
            return False

    return True


# ========== Content Analysis Functions ==========

def has_image_content(content):
    """Check if the message content contains any image content."""
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "image_url":
                return True
    return False


def extract_text_content(content):
    """Extract text content from a message content, which may be a string or a list of content parts."""
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                return item.get("text", "")
        return ""  # Return empty if no text content found
    else:
        return content  # Assume it's a string


def generate_summary(client, messages, provider, config):
    """Generate a summary of the conversation for use as filename"""
    try:
        # Extract text-only content from all messages for summary generation
        text_only_messages = []
        for msg in messages:
            text_content = extract_text_content(msg.get("content", ""))
            if text_content:
                text_only_messages.append({
                    "role": msg["role"],
                    "content": text_content
                })

        # Create a prompt for generating a concise summary
        summary_prompt = [
            {"role": "system", "content": "You are a helpful assistant that creates very concise, 3-5 word summaries of conversations. Respond with only the summary text, no additional commentary."},
            {"role": "user", "content": f"Please provide a very concise 3-5 word summary of this conversation. Focus on the main topic or theme:\n\n{json.dumps(text_only_messages, ensure_ascii=False)}"}
        ]

        response = client.chat.completions.create(
            model=config["model_providers"][provider]["generate_summary_model"],
            messages=summary_prompt,
            temperature=0.1,  # Low temperature for consistent output
        )

        summary = response.choices[0].message.content.strip()

        # Clean up the summary for filename use
        summary = re.sub(r'[^\w\s-]', '', summary)  # Remove special characters
        summary = re.sub(r'[-\s]+', '_', summary)   # Replace spaces and hyphens with underscores
        summary = summary.lower()                   # Convert to lowercase
        summary = summary[:50]                      # Limit length

        return summary if summary else "conversation"

    except Exception as e:
        print_error(f"\033[1;31m[SUMMARY] Failed to generate summary: {str(e)}\033[0m")
        return None


# ========== Command Processing Functions ==========

def is_command_input(input_text, config):
    """Check if input is a direct command (starts with '!')."""
    bash_config = config.get("bash_commands", {})
    prefix = bash_config.get("command_prefix", "!")
    return input_text.strip().startswith(prefix)


def extract_command(input_text, config):
    """Extract the actual command from input (remove prefix)."""
    bash_config = config.get("bash_commands", {})
    prefix = bash_config.get("command_prefix", "!")
    return input_text.strip()[len(prefix):].strip()


def validate_command_safety(command, config):
    """Validate if the command is safe to execute."""
    bash_config = config.get("bash_commands", {})

    # Check if command is empty
    if not command.strip():
        return False

    # Extract the first word (command name)
    cmd_name = command.strip().split()[0].lower()

    # Check against dangerous commands
    dangerous_commands = bash_config.get("dangerous_commands", [])
    if cmd_name in dangerous_commands:
        print(f"\033[1;31m[BASH] Dangerous command blocked: {cmd_name}\033[0m")
        return False

    return True


def execute_command(command, config):
    """Safely execute a command and return the execution result."""
    bash_config = config.get("bash_commands", {})
    timeout_seconds = bash_config.get("timeout_seconds", 30)
    max_output_length = bash_config.get("max_output_length", 10000)

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        stdout, stderr = process.communicate(timeout=timeout_seconds)
        return_code = process.returncode

        # Apply output length limits
        if len(stdout) > max_output_length:
            stdout = stdout[:max_output_length] + "\n[Output truncated]"

        if len(stderr) > max_output_length:
            stderr = stderr[:max_output_length] + "\n[Error output truncated]"

        # Return execution result
        return {
            "command": command,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code
        }

    except subprocess.TimeoutExpired:
        print(f"\033[1;31m[BASH] Command timed out after {timeout_seconds} seconds\033[0m")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        return {
            "command": command,
            "stdout": "",
            "stderr": f"Command timed out after {timeout_seconds} seconds",
            "return_code": -1
        }
    except Exception as e:
        print(f"\033[1;31m[BASH] Command execution failed: {str(e)}\033[0m")
        return {
            "command": command,
            "stdout": "",
            "stderr": f"Command execution failed: {str(e)}",
            "return_code": -1
        }


def format_command_output(command, stdout, stderr, return_code, program_color):
    """Format and display command execution results."""
    print(f"\033[1;{program_color}m[BASH] Command: {command}\033[0m")
    print(f"\033[1;{program_color}m[BASH] Return code: {return_code}\033[0m")

    if stdout:
        print(f"\033[1;32m[BASH] Output:\033[0m")
        print(stdout)

    if stderr:
        print(f"\033[1;31m[BASH] Errors:\033[0m")
        print(stderr)

    if return_code == 0 and not stdout and not stderr:
        print(f"\033[1;33m[BASH] Command completed successfully (no output)\033[0m")


def add_command_result_to_messages(result, messages):
    """Add command execution result to messages as context."""
    command = result["command"]
    return_code = result["return_code"]
    stdout = result["stdout"]
    stderr = result["stderr"]

    # Create a formatted message with the command and its result
    bash_result_message = f"\n[System Command Executed]\n"
    bash_result_message += f"Command: {command}\n"
    bash_result_message += f"Exit Code: {return_code}\n"

    if stdout:
        bash_result_message += f"Output:\n{stdout}\n"

    if stderr:
        bash_result_message += f"Errors:\n{stderr}\n"

    # Add as a user message to provide context to AI
    messages.append({
        "role": "user",
        "content": bash_result_message
    })


def process_user_command(user_input, config, messages, program_color):
    """Process a user command and update messages if executed."""
    command = extract_command(user_input, config)
    if validate_command_safety(command, config):
        # Execute command first (existing pre-execution confirmation still applies)
        result = execute_command(command, config)
        if result:
            # Format and display output
            format_command_output(command, result["stdout"], result["stderr"], result["return_code"], program_color)
            
            # Add post-execution confirmation for adding results to messages
            print(f"\033[1;{program_color}m[BASH] Add command results to conversation? (Y/n): \033[0m", end="")
            try:
                response = input().strip().lower()
                if response in ['', 'y', 'yes']:
                    add_command_result_to_messages(result, messages)
                    print(f"\033[1;32m[BASH] Command results added to conversation\033[0m")
                else:
                    print(f"\033[1;33m[BASH] Command results not added to conversation\033[0m")
            except (KeyboardInterrupt, EOFError):
                print(f"\033[1;{program_color}m[BASH] Command results not added to conversation\033[0m")
            return True
    return True


# ========== Initialization Functions ==========

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

def load_env_file(script_dir):
    """Load environment variables from .env file."""
    env_path = os.path.join(script_dir, ".env")
    try:
        load_dotenv(dotenv_path=env_path)
    except Exception as e:
        print_error(f"\033[1;31m[CRITICAL] Failed to load .env file: {str(e)}\033[0m")
        exit(1)


def initialize_openai_client(script_dir, provider=None, config=None):
    """Initialize OpenAI client with configuration from config.json."""
    # Load environment variables first using existing function
    load_env_file(script_dir)
    
    try:
        # Get API key environment variable name
        provider_config = config["model_providers"][provider]
        api_key_env = provider_config.get("api_key_env")
        if not api_key_env:
            raise ValueError(f"No api_key_env configured for provider '{provider}'")

        api_key = os.getenv(api_key_env)
        if not api_key:
            raise ValueError(f"API key not found in environment variable '{api_key_env}'")
        
        # Get base URL
        base_url = provider_config.get("base_url")
        if not base_url:
            raise ValueError(f"No base_url configured for provider '{provider}'")
        
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        
        return client
    except Exception as e:
        print_error(f"\033[1;31m[INIT] {str(e)}\033[0m")
        exit(1)

def print_conversation(chat_file, config=None):
    """Print a saved conversation from a JSON file with colored formatting."""
    try:
        with open(chat_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Extract conversation messages
        messages = data.get("messages", [])
        metadata = data.get("metadata", {})

        # Use colors from config if provided, otherwise use defaults
        user_color = config["colors"]["user"]
        assistant_color = config["colors"]["assistant"]
        program_color = config["colors"]["program"]

        print(f"\033[1;{program_color}m{'='*60}\033[0m")
        print(f"\033[1;{program_color}mConversation File: {chat_file}\033[0m")

        # Print metadata information using program_color
        if metadata:
            model_info = metadata.get("model", "Unknown")
            temperature = metadata.get("temperature", "Unknown")
            saved_at = metadata.get("saved_at", "Unknown")

            # Format saved_at timestamp for better readability
            if saved_at != "Unknown":
                dt = datetime.datetime.fromisoformat(saved_at)
                saved_at = dt.strftime("%Y-%m-%d %H:%M:%S")

            print(f"\033[1;{program_color}mModel: {model_info} | Temperature: {temperature}\033[0m")
            print(f"\033[1;{program_color}mSaved at: {saved_at}\033[0m")

        print(f"\033[1;{program_color}m{'='*60}\033[0m")

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            # Handle multimodal content (e.g., image + text)
            if isinstance(content, list):
                # Extract text content
                text_content = ""
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_content = item.get("text", "")
                        break
                content = text_content if text_content else "[Multimodal content (e.g., image)]"

            if role == "user":
                print(f"\n\033[1;{user_color}mUser Question:\033[0m\n\n{content}")
            elif role == "assistant":
                print(f"\n\033[1;{assistant_color}mAssistant Answer:\033[0m\n\n{content}")

    except FileNotFoundError:
        print_error(f"Error: File '{chat_file}' not found.")
    except json.JSONDecodeError:
        print_error(f"Error: File '{chat_file}' is not a valid JSON format.")
    except Exception as e:
        print_error(f"Error reading file: {str(e)}")

def get_common_parser():
    """Return common argument parser for both Linux and Windows versions."""
    parser = argparse.ArgumentParser(description="A CLI client for interacting with AI chat models.")
    parser.add_argument('-m', '--model', default='ecnu-max',
                      help="Model selection in format 'provider:model' or 'model'. "
                           "Examples: 'ecnu:ecnu-max', 'deepseek:deepseek-chat', 'ecnu-reasoner'. "
                           "If no provider specified, uses default from config.json")
    parser.add_argument('-p', '--prompt-file', default=None,
                      help="Custom system prompt file path")
    parser.add_argument('-t', '--temperature', type=float, default=None,
                      help="Temperature parameter (default: v3=0.3, r1=0.6)")
    parser.add_argument('-f', '--files', default=None, nargs='+',
                      help="Paths to text files to upload as initial context (multiple files allowed)")
    parser.add_argument('-i', '--images', default=None, nargs='+',
                      help="Paths to image files for vision model interaction (multiple files allowed)")
    parser.add_argument('-l', '--load-chat', default=None,
                      help="Path to a saved chat JSON file to load and continue conversation")

    # print saved conversations
    parser.add_argument('-P', '--print-chat', default=None,
                      help="Path to a saved chat JSON file to print its content")

    # non-interactive mode
    parser.add_argument('-s', '--silent', default=None,
                  help="Input text for silent (non-interactive) mode (if provided, program will process and exit)")

    return parser
