"""
ChatECNU CLI - Core Chat Session Management
Contains the core ChatSession class with essential chat functionality.
"""

import datetime
import json
import os
import re
import sys

# Import utility functions at module level
from utils import (
    add_file_contents,
    add_image_contents,
    has_image_content,
    extract_text_content,
    generate_summary,
    is_command_input,
    extract_command,
    validate_command_safety,
    execute_command,
    format_command_output,
    add_command_result_to_messages,
    process_user_command,
    print_error
)


class ChatSession:
    """Core chat session management for ECNU AI chat models."""

    def __init__(self, provider, model, temperature, system_prompt, file_paths, image_paths, load_chat_file, script_dir, config):
        # Store configuration
        self.config = config
        self.script_dir = script_dir
        self.provider = provider
        self.model = model

        # Check if provider exists in config
        if self.provider not in config["model_providers"]:
            raise ValueError(f"Provider '{self.provider}' not found in config")

        provider_config = config["model_providers"][self.provider]

        # Check if model exists in provider
        if self.model not in config["model_providers"][self.provider]["models"]:
            raise ValueError(f"Model '{self.model}' not found in provider '{self.provider}'")

        # Use vision model if images provided
        if image_paths:
            vision_model = provider_config.get("vision_model")
            if vision_model:
                self.model = vision_model
            else:
                print_error(f"\033[1;31m[CONFIG] No vision model available for provider '{self.provider}'\033[0m")
                raise

        # Use colors from config
        self.user_color = self.config["colors"]["user"]
        self.program_color = self.config["colors"]["program"]
        self.assistant_color = self.config["colors"]["assistant"]
        self.reasoning_color = self.config["colors"]["reasoning"]

        self.model = model
        self.temperature = self._get_model_temp(temperature)
        self.system_prompt = self._get_system_prompt(system_prompt)
        self.file_paths = file_paths
        self.image_paths = image_paths
        self.load_chat_file = load_chat_file

        self.messages = [{"role": "system", "content": self.system_prompt}]

        # Load conversation history if specified
        if load_chat_file and not self.load_conversation(load_chat_file):
            raise ValueError(f"Failed to load conversation from {load_chat_file}")

        # Process files and images using utility functions
        if file_paths:
            if not add_file_contents(file_paths, self.messages):
                raise ValueError("Failed to process one or more files")
        if image_paths:
            if not add_image_contents(image_paths, self.messages):
                raise ValueError("Failed to process one or more images")

    def _get_model_temp(self, temperature):
        """Get default temperature for model from config"""
        if temperature:
            return temperature
        else:
            return self.config["model_providers"][self.provider]["models"][self.model].get("temperature_defaults", 0.3)

    def _get_system_prompt(self, system_prompt):
        """Load system prompt from file from config"""
        if system_prompt:
            if not os.path.exists(system_prompt):
                raise FileNotFoundError(f"Prompt file not found: {system_prompt}")
            prompt_path = system_prompt
        else:
            # Use prompt mapping from config
            prompts_dir = self.config["paths"]["prompts_dir"]
            default_file = self.config["model_providers"][self.provider]["models"][self.model].get("prompt_defaults")
            prompt_path = os.path.join(self.script_dir, prompts_dir, default_file)

        try:
            with open(prompt_path, "r", encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise ValueError("Prompt file is empty")
            return content
        except Exception as e:
            print_error(f"\033[1;31m[LOAD] Failed to load prompt: {str(e)}\033[0m")
            raise

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
                if "reasoner" in self.model and chunk.choices and chunk.choices[0].delta.reasoning_content:
                    reasoning_content = chunk.choices[0].delta.reasoning_content

                    # Add prefix and separator when reasoning content first appears
                    if not reasoning_started:
                        print(f"\033[1;{self.assistant_color}m{'='*30} Think {'='*30}\033[0m", flush=True)
                        print(f"\033[1;{self.reasoning_color}m", end="", flush=True)
                        reasoning_started = True

                    print(reasoning_content, end="", flush=True)

                if chunk.choices and chunk.choices[0].delta.content:
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

    def save_conversation(self, client):
        """Save the current conversation history and session metadata to a JSON file."""
        if len(self.messages) <= 1:
            print_error(f"\033[1;31m[SAVE] No conversation content to save (only system prompt exists).\033[0m")
            return False

        # Use saved_chats_dir from config
        saved_chats_dir = os.path.join(self.script_dir, self.config["paths"]["saved_chats_dir"])
        os.makedirs(saved_chats_dir, exist_ok=True)

        # Generate summary for filename
        summary = generate_summary(client, self.messages, self.provider, self.config)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if summary:
            filename = f"chat_{timestamp}_{summary}.json"
        else:
            filename = f"chat_{timestamp}.json"

        filepath = os.path.join(saved_chats_dir, filename)

        # Create a structured object containing both metadata and messages
        # Save provider:model format for compatibility
        full_model_name = f"{self.provider}:{self.model}" if self.provider else self.model

        conversation_data = {
            "metadata": {
                "model": full_model_name,  # Save as provider:model format
                "temperature": self.temperature,
                "system_prompt": self.system_prompt,
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
                # Update provider and model from loaded data if available
                loaded_model = metadata.get("model", self.model)

                # Parse provider:model format from loaded data
                if ":" in loaded_model:
                    loaded_provider, loaded_model = loaded_model.split(":", 1)
                    self.provider = loaded_provider
                    self.model = loaded_model
                else:
                    self.model = loaded_model
                    # Determine provider from config
                    for provider_name, provider_config in self.config["model_providers"].items():
                        if loaded_model in provider_config.get("models", {}):
                            self.provider = provider_name
                            break

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
                if has_image_content(msg.get("content", "")):
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
        print(f"\033[1;{self.program_color}mModel: {self.model} | Temperature: {self.temperature}\033[0m")
        print(f"\033[1;{self.program_color}m(Type 'q' to quit, 's' to save, 'c' to clear, use\033[0m \033[1;33m'!<command>'\033[0m \033[1;{self.program_color}mto execute system commands)\033[0m")

        if self.file_paths:
            print(f"\033[1;33m{len(self.file_paths)} file(s) have been loaded. You can now ask questions about them.\033[0m")
        if self.image_paths:
            print(f"\033[1;33m{len(self.image_paths)} image(s) have been loaded. You can now ask questions about them.\033[0m")

        if self.load_chat_file:
            print(f"\033[1;33m[LOAD] Conversation loaded from {self.load_chat_file}\033[0m")
            user_messages = [msg for msg in self.messages if msg["role"] == "user"]
            for i, msg in enumerate(user_messages, 1):
                text_content = extract_text_content(msg.get("content", ""))
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
                elif is_command_input(user_input, self.config):
                    # Handle direct bash command through command processor
                    processed = process_user_command(user_input, self.config, self.messages, self.program_color)
                    if processed:
                        continue
                if not user_input:
                    continue

                try:
                    self.add_user_message(user_input)
                    success = self.generate_assistant_response(client)
                    if not success:
                        print_error("\033[1;31m[ERROR] Conversation error, please try again\033[0m")

                except ValueError as e:
                    print_error(f"\033[1;31m[INPUT] {str(e)}\033[0m")

            except KeyboardInterrupt:
                print(f"\033[1;{self.program_color}mSession terminated by Ctrl+C\033[0m")
                break
            except Exception as e:
                print_error(f"\033[1;31m[FATAL] Unexpected error: {str(e)}\033[0m")
                break
