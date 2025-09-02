#!/usr/bin/env python3
import argparse
import base64
import datetime
import json
import os
import re
import readline

from dotenv import load_dotenv
from openai import OpenAI

# Get absolute path of current script (resolving symlinks)
script_path = os.path.realpath(__file__)
script_dir = os.path.dirname(script_path)

# Construct path to .env file
env_path = os.path.join(script_dir, ".env")

# Explicitly load .env from specified path
try:
    load_dotenv(dotenv_path=env_path)
except Exception as e:
    print(f"\033[1;31m[CRITICAL] Failed to load .env file: {str(e)}\033[0m")
    exit(1)

class ChatSession:
    def __init__(self, model, temperature, system_prompt, file_paths, image_paths, load_chat_file):
        if image_paths:
            model = "vl"        # Use vision model if images provided
        self.user_color = "32"  # Green
        self.program_color = "36"  # Cyan
        self.assistant_color = "34"  # Blue
        self.reasoning_color = "33"  # Yellow
        self.model = self._get_model_name(model)
        self.system_prompt = self._get_system_prompt(system_prompt)
        self.file_paths = file_paths
        self.image_paths = image_paths
        self.load_chat_file = load_chat_file

        if temperature:
            self.temperature = temperature
        else:
            self.temperature = self._get_model_temp(model)

        self.messages = [{"role": "system", "content": self.system_prompt}]

        # Load conversation history if specified
        if load_chat_file and not self.load_conversation(load_chat_file):
            raise ValueError(f"Failed to load conversation from {load_chat_file}")

        # Process files and images
        if file_paths and not self.add_file_contents(file_paths):
            raise ValueError("Failed to process one or more files")
        if image_paths and not self.add_image_contents(image_paths):
            raise ValueError("Failed to process one or more images")

    def _get_model_name(self, model_flag):
        """Map model flag to actual model name"""
        model_mapping = {
            "r1": "ecnu-reasoner",
            "v3": "ecnu-max",
            "vl": "ecnu-vl",
        }
        return model_mapping.get(model_flag, "ecnu-max")

    def _get_model_temp(self, model_flag):
        """Get default temperature for model"""
        model_mapping = {
            "r1": 0.6,
            "v3": 0.3,
            "vl": 0.01,
        }
        return model_mapping.get(model_flag, 0.3)

    def _get_system_prompt(self, system_prompt):
        """Load system prompt from file"""
        if system_prompt:
            if not os.path.exists(system_prompt):
                raise FileNotFoundError(f"Prompt file not found: {system_prompt}")
            prompt_path = system_prompt
        else:
            default_file = "ecnu-r1.md" if self.model == "r1" else "ecnu-v3.md"
            prompt_path = os.path.join(script_dir, default_file)

        try:
            with open(prompt_path, "r", encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise ValueError("Prompt file is empty")
            return content
        except Exception as e:
            print(f"\033[1;31m[LOAD] Failed to load prompt: {str(e)}\033[0m")
            raise

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

    def add_user_message(self, content):
        """Add user message to conversation history"""
        if not content or not isinstance(content, str):
            raise ValueError("Message content must be non-empty string")
        self.messages.append({"role": "user", "content": content})

    def generate_assistant_response(self):
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
            print(f"\n\033[1;31m[NETWORK] Connection failed: {str(e)}\033[0m")
            return False
        except TimeoutError as e:
            print(f"\n\033[1;31m[TIMEOUT] Request timed out: {str(e)}\033[0m")
            return False
        except Exception as e:
            print(f"\n\033[1;31m[API] Error occurred: {str(e)}\033[0m")
            return False

    def generate_summary(self):
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
            print(f"\033[1;31m[SUMMARY] Failed to generate summary: {str(e)}\033[0m")
            return None

    def add_file_contents(self, file_paths):
        """Add multiple file contents to conversation context"""
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"\033[1;31m[FILE] File not found: {file_path}\033[0m")
                return False

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_content = f.read()

                if not file_content.strip():
                    print(f"\033[1;31m[WARNING] Empty file: {file_path}\033[0m")
                    continue

                self.messages.append({
                    "role": "user",
                    "content": f"User has uploaded a file '{os.path.basename(file_path)}'. Here is its content:\n{file_content}"
                })
            except UnicodeDecodeError:
                print(f"\033[1;31m[FILE] Not a UTF-8 encoded file: {file_path}\033[0m")
                return False
            except PermissionError:
                print(f"\033[1;31m[FILE] Permission denied: {file_path}\033[0m")
                return False
            except Exception as e:
                print(f"\033[1;31m[FILE] Error reading file {file_path}: {str(e)}\033[0m")
                return False

        return True

    def add_image_contents(self, image_paths):
        """Add multiple image contents to conversation context"""
        for image_path in image_paths:
            if not os.path.exists(image_path):
                print(f"\033[1;31m[IMAGE] File not found: {image_path}\033[0m")
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
                print(f"\033[1;31m[IMAGE] Permission denied: {image_path}\033[0m")
                return False
            except Exception as e:
                print(f"\033[1;31m[IMAGE] Error processing image {image_path}: {str(e)}\033[0m")
                return False

        return True

    def save_conversation(self):
        """Save the current conversation history and session metadata to a JSON file."""
        if len(self.messages) <= 1:
            print(f"\033[1;31m[SAVE] No conversation content to save (only system prompt exists).\033[0m")
            return False

        saved_chats_dir = os.path.join(script_dir, "saved_chats")
        os.makedirs(saved_chats_dir, exist_ok=True)

        # Generate summary for filename
        summary = self.generate_summary()
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
            print(f"\033[1;31m[SAVE] Failed to save conversation: {str(e)}\033[0m")
            return False

    def load_conversation(self, chat_file_path):
        """Load conversation history and session metadata from a JSON file."""
        try:
            if not os.path.exists(chat_file_path):
                print(f"\033[1;31m[LOAD] Chat file not found: {chat_file_path}\033[0m")
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
                print(f"\033[1;31m[LOAD] Invalid chat file format\033[0m")
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
            print(f"\033[1;31m[LOAD] Invalid JSON format in chat file\033[0m")
            return False
        except Exception as e:
            print(f"\033[1;31m[LOAD] Error loading conversation: {str(e)}\033[0m")
            return False

    def start(self):
        print(f"\033[1;{self.program_color}mECNU Chat Client\033[0m\n")
        print(f"\033[1;{self.program_color}mModel: {self.model} | Temperature: {self.temperature}\033[0m")
        print(f"\033[1;{self.program_color}m(Type 'exit' to quit, 'save' to save conversation)\033[0m")

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
                print(f"\n\033[1;{self.user_color}mUser: (Input text then press Ctrl+D to submit)\033[0m\n")

                lines = []
                while True:
                    try:
                        line = input()
                    except EOFError:
                        break
                    except KeyboardInterrupt:
                        print(f"\033[1;{self.program_color}mSession terminated by Ctrl+C\033[0m")
                        return
                    lines.append(line)
                    if line.strip().lower() in ['exit', 'quit', 'save', 'q', 's']:
                        break

                user_input = "\n".join(lines).strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print(f"\033[1;{self.program_color}mExiting...\033[0m")
                    break
                elif user_input.lower() in ['save', 's']:
                    self.save_conversation()
                    continue
                if not user_input:
                    continue

                try:
                    self.add_user_message(user_input)
                    if not self.generate_assistant_response():
                        print("\033[1;31m[ERROR] Conversation error, please try again\033[0m")
                except ValueError as e:
                    print(f"\033[1;31m[INPUT] {str(e)}\033[0m")

            except KeyboardInterrupt:
                print(f"\033[1;{self.program_color}mSession terminated by Ctrl+C\033[0m")
                break
            except Exception as e:
                print(f"\033[1;31m[FATAL] Unexpected error: {str(e)}\033[0m")
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A CLI client for interacting with ECNU's AI chat models.")
    parser.add_argument('-m', '--model', default='v3', choices=['v3', 'r1'],
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
    args = parser.parse_args()

    try:
        client = OpenAI(
            api_key=os.getenv("CHATECNU_API_KEY"),
            base_url="https://chat.ecnu.edu.cn/open/api/v1",
        )
        if not client.api_key:
            raise ValueError("API key not configured")
    except Exception as e:
        print(f"\033[1;31m[INIT] {str(e)}\033[0m")
        exit(1)

    try:
        session = ChatSession(
            model=args.model,
            temperature=args.temperature,
            system_prompt=args.prompt_file,
            file_paths=args.files,
            image_paths=args.images,
            load_chat_file=args.load_chat
        )

        session.start()
    except Exception as e:
        print(f"\033[1;31m[SESSION] Failed to start session: {str(e)}\033[0m")
        exit(1)
