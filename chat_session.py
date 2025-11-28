#!/usr/bin/env python3
"""
ChatECNU CLI - Shared Chat Session Module
Contains the core ChatSession class and common functionality for both Linux and Windows versions.
"""

import argparse
import base64
import datetime
import json
import os
import re
import sys

from dotenv import load_dotenv
from openai import OpenAI


def print_error(message):
    """Print error message to stderr with proper formatting."""
    print(message, file=sys.stderr)


class ChatSession:
    """Core chat session management for ECNU AI chat models."""

    def __init__(self, model, temperature, system_prompt, file_paths, image_paths, load_chat_file, script_dir, command_processor=None):
        # Load configuration
        self.config = self.load_config(script_dir)
        self.script_dir = script_dir

        if image_paths:
            model = "vl"  # Use vision model if images provided

        # Use colors from config
        self.user_color = self.config["colors"]["user"]
        self.program_color = self.config["colors"]["program"]
        self.assistant_color = self.config["colors"]["assistant"]
        self.reasoning_color = self.config["colors"]["reasoning"]

        self.model = self._get_model_name(model)
        self.temperature = self._get_model_temp(temperature)
        self.system_prompt = self._get_system_prompt(system_prompt)
        # Store the original system prompt for saving conversations
        self.original_system_prompt = self.system_prompt
        self.file_paths = file_paths
        self.image_paths = image_paths
        self.load_chat_file = load_chat_file
        # Update command processor with the actual configuration if provided
        self.command_processor = command_processor
        if self.command_processor:
            # Update the command processor with the actual loaded configuration
            self.command_processor.config = self.config
            self.command_processor.bash_config = self.config.get("bash_commands", {})
            self.command_processor.enabled = self.command_processor.bash_config.get("enabled", False)

        self.messages = [{"role": "system", "content": self.system_prompt}]

        # Load conversation history if specified
        if load_chat_file and not self.load_conversation(load_chat_file):
            raise ValueError(f"Failed to load conversation from {load_chat_file}")

        # Process files and images
        if file_paths and not self.add_file_contents(file_paths):
            raise ValueError("Failed to process one or more files")
        if image_paths and not self.add_image_contents(image_paths):
            raise ValueError("Failed to process one or more images")

    def load_config(self, script_dir):
        """Load configuration using simplified config loader."""
        try:
            from config import load_config
            return load_config(script_dir)
        except FileNotFoundError:
            print_error(f"\033[1;31m[CONFIG] Configuration file not found\033[0m")
            exit(1)
        except json.JSONDecodeError:
            print_error(f"\033[1;31m[CONFIG] Invalid JSON format in config file\033[0m")
            exit(1)
        except Exception as e:
            print_error(f"\033[1;31m[CONFIG] Error loading config: {str(e)}\033[0m")
            exit(1)

    def _get_model_name(self, model_flag):
        """Map model flag to actual model name from config"""
        model_mapping = self.config["model_name"]
        return model_mapping.get(model_flag, self.config["model_name"]["default"])

    def _get_model_temp(self, temperature):
        """Get default temperature for model from config"""
        model_mapping = self.config["temperature_defaults"]

        if temperature:
            return temperature
        else:
            return model_mapping.get(self.model, self.config["temperature_defaults"]["default"])

    def _get_system_prompt(self, system_prompt):
        """Load system prompt from file from config"""
        if system_prompt:
            if not os.path.exists(system_prompt):
                raise FileNotFoundError(f"Prompt file not found: {system_prompt}")
            prompt_path = system_prompt
        else:
            # Use prompt mapping from config
            prompts_dir = self.config["paths"]["prompts_dir"]
            prompt_mapping = self.config["prompt_defaults"]
            default_file = prompt_mapping.get(self.model, self.config["prompt_defaults"]["default"])
            prompt_path = os.path.join(self.script_dir, prompts_dir, default_file)

            # If bash mode is enabled, use the bash-specific prompt
            bash_enabled = self.config.get("bash_commands", {}).get("enabled", False)
            if bash_enabled:
                bash_prompt_path = os.path.join(self.script_dir, prompts_dir, "ecnu-bash.md")
                if os.path.exists(bash_prompt_path):
                    prompt_path = bash_prompt_path

        try:
            with open(prompt_path, "r", encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise ValueError("Prompt file is empty")
            return content
        except Exception as e:
            print_error(f"\033[1;31m[LOAD] Failed to load prompt: {str(e)}\033[0m")
            raise

    def _reload_system_prompt(self):
        """Reload system prompt based on current configuration."""
        try:
            new_system_prompt = self._get_system_prompt(None)  # 使用当前配置重新加载

            # 更新系统提示词
            self.system_prompt = new_system_prompt

            # 更新消息列表中的系统消息（如果有）
            if self.messages and self.messages[0]["role"] == "system":
                self.messages[0]["content"] = new_system_prompt

        except Exception as e:
            print_error(f"\033[1;31m[PROMPT] Failed to reload system prompt: {str(e)}\033[0m")

    def _has_image_content(self, content):
        """Check if the message content contains any image content."""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    return True
        return False

    def _extract_text_content(self, content):
        """Extract text content from a message content, which may be a string or a list of content parts."""
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")
            return ""  # Return empty if no text content found
        else:
            return content  # Assume it's a string

    def generate_silent_response(self, client):
        """Generate assistant response without streaming output (for non-interactive mode)."""
        try:
            # Use non-streaming API call to get complete response
            response = client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=False,
                temperature=self.temperature,
            )

            response_content = response.choices[0].message.content

            return response_content

        except ConnectionError as e:
            print_error(f"\n\033[1;31m[NETWORK] Connection failed: {str(e)}\033[0m")
            return None
        except TimeoutError as e:
            print_error(f"\n\033[1;31m[TIMEOUT] Request timed out: {str(e)}\033[0m")
            return None
        except Exception as e:
            print_error(f"\n\033[1;31m[API] Error occurred: {str(e)}\033[0m")
            return None

    def add_user_message(self, content):
        """Add user message to conversation history"""
        if not content or not isinstance(content, str):
            raise ValueError("Message content must be non-empty string")
        self.messages.append({"role": "user", "content": content})

    def generate_assistant_response(self, client):
        """Generate assistant response with streaming output"""
        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True,
                temperature=self.temperature,
            )

            full_response = []
            print(f"\n\033[1;{self.assistant_color}mAssistant: \033[0m\n", flush=True)

            # Add reasoning process identifier
            reasoning_started = False

            for chunk in stream:
                if "reasoner" in self.model and chunk.choices[0].delta.reasoning_content:
                    reasoning_content = chunk.choices[0].delta.reasoning_content

                    # Add prefix and separator when reasoning content first appears
                    if not reasoning_started:
                        print(f"\033[1;{self.assistant_color}m{'='*30} Think {'='*30}\033[0m", flush=True)
                        print(f"\033[1;{self.reasoning_color}m", end="", flush=True)
                        reasoning_started = True

                    print(reasoning_content, end="", flush=True)

                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content

                    # Add separator after reasoning
                    if reasoning_started:
                        print("\033[0m")  # End reasoning color
                        print(f"\033[1;{self.assistant_color}m{'='*30} Answer {'='*30}\033[0m")
                        reasoning_started = False

                    print(content, end="", flush=True)
                    full_response.append(content)
            print()

            self.messages.append({"role": "assistant", "content": "".join(full_response)})
            return True

        except ConnectionError as e:
            print_error(f"\n\033[1;31m[NETWORK] Connection failed: {str(e)}\033[0m")
            return False
        except TimeoutError as e:
            print_error(f"\n\033[1;31m[TIMEOUT] Request timed out: {str(e)}\033[0m")
            return False
        except Exception as e:
            print_error(f"\n\033[1;31m[API] Error occurred: {str(e)}\033[0m")
            return False

    def generate_summary(self, client):
        """Generate a summary of the conversation for use as filename"""
        try:
            # Extract text-only content from all messages for summary generation
            text_only_messages = []
            for msg in self.messages:
                text_content = self._extract_text_content(msg.get("content", ""))
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
                model='ecnu-max',
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

    def add_file_contents(self, file_paths):
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

                self.messages.append({
                    "role": "user",
                    "content": f"User has uploaded a file '{os.path.basename(file_path)}'. Here is its content:\n{file_content}"
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

    def add_image_contents(self, image_paths):
        """Add multiple image contents to conversation context"""
        for image_path in image_paths:
            if not os.path.exists(image_path):
                print_error(f"\033[1;31m[IMAGE] File not found: {image_path}\033[0m")
                return False

            try:
                with open(image_path, "rb") as image_file:
                    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

                self.messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"User has uploaded an image '{os.path.basename(image_path)}', please remember its content."},
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

    def save_conversation(self, client):
        """Save the current conversation history and session metadata to a JSON file."""
        if len(self.messages) <= 1:
            print_error(f"\033[1;31m[SAVE] No conversation content to save (only system prompt exists).\033[0m")
            return False

        # Use saved_chats_dir from config
        saved_chats_dir = os.path.join(self.script_dir, self.config["paths"]["saved_chats_dir"])
        os.makedirs(saved_chats_dir, exist_ok=True)

        # Generate summary for filename
        summary = self.generate_summary(client)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if summary:
            filename = f"chat_{timestamp}_{summary}.json"
        else:
            filename = f"chat_{timestamp}.json"

        filepath = os.path.join(saved_chats_dir, filename)

        # Create a structured object containing both metadata and messages
        conversation_data = {
            "metadata": {
                "model": self.model,
                "temperature": self.temperature,
                "system_prompt": self.original_system_prompt,  # Use original prompt, not current one
                "saved_at": datetime.datetime.now().isoformat()
            },
            "messages": self.messages[1:]
        }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=4, ensure_ascii=False)
            print(f"\033[1;{self.program_color}m[SAVE] Conversation saved to {filepath}\033[0m")
            return True
        except Exception as e:
            print_error(f"\033[1;31m[SAVE] Failed to save conversation: {str(e)}\033[0m")
            return False

    def load_conversation(self, chat_file_path):
        """Load conversation history and session metadata from a JSON file."""
        try:
            if not os.path.exists(chat_file_path):
                print_error(f"\033[1;31m[LOAD] Chat file not found: {chat_file_path}\033[0m")
                return False

            # Read and parse the JSON file
            with open(chat_file_path, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)

            if isinstance(loaded_data, dict) and "metadata" in loaded_data and "messages" in loaded_data:
                metadata = loaded_data["metadata"]
                self.model = metadata.get("model", self.model)
                self.temperature = metadata.get("temperature", self.temperature)
                self.system_prompt = metadata.get("system_prompt", self.system_prompt)
                loaded_messages = loaded_data["messages"]

            # Validate the loaded messages structure
            if not isinstance(loaded_messages, list) or len(loaded_messages) == 0:
                print_error(f"\033[1;31m[LOAD] Invalid chat file format\033[0m")
                return False

            # Check if any message contains image content
            has_images = False
            for msg in loaded_messages:
                if self._has_image_content(msg.get("content", "")):
                    has_images = True
                    break

            # If images are detected, switch to vision model
            if has_images and self.model != "ecnu-vl":
                self.model = "ecnu-vl"
                self.temperature = self._get_model_temp("vl")

            # Replace current messages with loaded ones (preserve system prompt)
            if loaded_messages[0]["role"] == "system":
                self.messages = loaded_messages
            else:
                self.messages = [{"role": "system", "content": self.system_prompt}] + loaded_messages

            return True

        except json.JSONDecodeError:
            print_error(f"\033[1;31m[LOAD] Invalid JSON format in chat file\033[0m")
            return False
        except Exception as e:
            print_error(f"\033[1;31m[LOAD] Error loading conversation: {str(e)}\033[0m")
            return False

    def start(self, client, input_handler, non_interactive_input=None):
        """Start the chat session with platform-specific input handling."""

        # Check if we're in non-interactive mode
        if non_interactive_input:
            # Non-interactive mode: process the input and return response
            try:
                self.add_user_message(non_interactive_input)

                # Generate response without streaming output (silent mode)
                response = self.generate_silent_response(client)
                if response:
                    print(response)
                else:
                    print_error("\033[1;31m[ERROR] Failed to generate response\033[0m")
            except Exception as e:
                print_error(f"\033[1;31m[ERROR] {str(e)}\033[0m")
            return

        # Interactive mode (original code)
        print(f"\033[1;{self.program_color}mECNU Chat Client\033[0m\n")

        # Show bash command mode status
        bash_enabled = self.config.get("bash_commands", {}).get("enabled", False)
        if bash_enabled:
            print(f"\033[1;{self.program_color}mModel: {self.model} | Temperature: {self.temperature} | Bash commands\033[0m \033[1;33menabled\033[0m")
            # print(f"\033[1;{self.program_color}m(Bash commands enabled - use '!<command>' to execute)\033[0m")
        else:
            print(f"\033[1;{self.program_color}mModel: {self.model} | Temperature: {self.temperature} | Bash commands\033[0m \033[1;33mdisabled\033[0m")
            # print(f"\033[1;{self.program_color}m(Bash commands disabled)\033[0m")

        print(f"\033[1;{self.program_color}m(Type 'q' to quit, 's' to save, 'c' to clear, 'bash on/off' to toggle commands)\033[0m")

        if self.file_paths:
            print(f"\033[1;33m{len(self.file_paths)} file(s) have been loaded. You can now ask questions about them.\033[0m")
        if self.image_paths:
            print(f"\033[1;33m{len(self.image_paths)} image(s) have been loaded. You can now ask questions about them.\033[0m")

        if self.load_chat_file:
            print(f"\033[1;33m[LOAD] Conversation loaded from {self.load_chat_file}\033[0m")
            user_messages = [msg for msg in self.messages if msg["role"] == "user"]
            for i, msg in enumerate(user_messages, 1):
                text_content = self._extract_text_content(msg.get("content", ""))
                if len(text_content) > 300:
                    text_content = text_content[:297] + "..."
                print(f"\033[1;{self.user_color}mUser Message {i}:\033[0m {text_content}")

        while True:
            try:
                user_input = input_handler()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print(f"\033[1;{self.program_color}mExiting...\033[0m")
                    break
                elif user_input.lower() in ['save', 's']:
                    self.save_conversation(client)
                    continue
                elif user_input.lower() in ['bash on', 'bash enable']:
                    if self.command_processor:
                        self.command_processor.toggle_mode(True, self._reload_system_prompt)
                    continue
                elif user_input.lower() in ['bash off', 'bash disable']:
                    if self.command_processor:
                        self.command_processor.toggle_mode(False, self._reload_system_prompt)
                    continue
                elif self.command_processor and self.command_processor.is_command_input(user_input):
                    # Handle direct bash command through command processor
                    processed = self.command_processor.process_user_command(user_input, self.messages)
                    if processed:
                        continue
                if not user_input:
                    continue

                try:
                    self.add_user_message(user_input)
                    success = self.generate_assistant_response(client)
                    if not success:
                        print_error("\033[1;31m[ERROR] Conversation error, please try again\033[0m")
                    else:
                        # Check if AI response contains bash commands using command processor
                        if self.messages and self.messages[-1]["role"] == "assistant":
                            ai_response = self.messages[-1]["content"]
                            if self.command_processor:
                                # Use the unified process_ai_commands method from CommandProcessor
                                processed = self.command_processor.process_ai_commands(ai_response, self.messages)
                                if processed:
                                    continue

                except ValueError as e:
                    print_error(f"\033[1;31m[INPUT] {str(e)}\033[0m")

            except KeyboardInterrupt:
                print(f"\033[1;{self.program_color}mSession terminated by Ctrl+C\033[0m")
                break
            except Exception as e:
                print_error(f"\033[1;31m[FATAL] Unexpected error: {str(e)}\033[0m")
                break


def load_env_file(script_dir):
    """Load environment variables from .env file."""
    env_path = os.path.join(script_dir, ".env")
    try:
        load_dotenv(dotenv_path=env_path)
    except Exception as e:
        print_error(f"\033[1;31m[CRITICAL] Failed to load .env file: {str(e)}\033[0m")
        exit(1)


def initialize_openai_client(script_dir):
    """Initialize OpenAI client with ECNU configuration."""
    # Load environment variables first using existing function
    load_env_file(script_dir)

    try:
        client = OpenAI(
            api_key=os.getenv("CHATECNU_API_KEY"),
            base_url="https://chat.ecnu.edu.cn/open/api/v1",
        )
        if not client.api_key:
            raise ValueError("API key not configured")
        return client
    except Exception as e:
        print_error(f"\033[1;31m[INIT] {str(e)}\033[0m")
        exit(1)


def get_common_parser():
    """Return common argument parser for both Linux and Windows versions."""
    parser = argparse.ArgumentParser(description="A CLI client for interacting with ECNU's AI chat models.")
    parser.add_argument('-m', '--model', default=None, choices=['v3', 'r1'],
                      help="Model selection: v3=ecnu-max (default), r1=ecnu-reasoner")
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

    # Add non-interactive mode support
    parser.add_argument('-P', '--print', default=None,
                      help="Input text for non-interactive mode (if provided, program will process and exit)")

    return parser
