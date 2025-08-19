#!/usr/bin/env python
import os
import readline
import argparse
from openai import OpenAI
from dotenv import load_dotenv

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
    def __init__(self, model, temperature, system_prompt, max_history=None, file_paths=None):
        self.user_color = "32"  # Green
        self.program_color = "36"  # Cyan
        self.assistant_color = "34"  # Blue
        self.reasoning_color = "33"  # Yellow
        self.model = self._get_model_name(model)
        self.temperature = temperature
        self.system_prompt = self._get_system_prompt(system_prompt)
        self.file_paths = file_paths

        if temperature:
            self.temperature = temperature
        else:
            self.temperature = self._get_model_temp(model)

        if max_history is None:
            self.max_history = 10 if "reasoner" in self.model else 15
        else:
            self.max_history = max_history

        self.messages = [{"role": "system", "content": self.system_prompt}]

        # Handle files if provided
        if file_paths and not self.add_file_contents(file_paths):
            raise ValueError("Failed to process one or more files")

    def _get_model_name(self, model_flag):
        """Convert flag to actual model name"""
        model_mapping = {
            "r1": "ecnu-reasoner",
            "v3": "ecnu-max",
        }
        return model_mapping.get(model_flag, "ecnu-max")

    def _get_model_temp(self, model_flag):
        """Get model's default temperature"""
        model_mapping = {
            "r1": 0.6,
            "v3": 0.3,
        }
        return model_mapping.get(model_flag, 0.3)

    def _get_system_prompt(self, system_prompt):
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

    def _trim_history(self):
        if len(self.messages) > self.max_history * 2 + 1:
            self.messages = [self.messages[0]] + self.messages[-self.max_history * 2:]

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
            self._trim_history()
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
                    print(f"\033[1;33m[WARNING] Empty file: {file_path}\033[0m")
                    continue

                self.messages.append({
                    "role": "system",
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


    def start(self):
        print(f"\033[1;{self.program_color}mECNU Chat Client (Type 'exit' to quit)\033[0m\n")
        print(f"\033[1;{self.program_color}mUsing model: {self.model} (Temperature: {self.temperature})\033[0m")
        print(f"\033[1;{self.program_color}mTip: Paste multi-line text and press Ctrl+D to submit\033[0m")

        if self.file_paths:
            print(f"\033[1;33m{len(self.file_paths)} file(s) have been loaded. You can now ask questions about them.\033[0m")

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

                user_input = "\n".join(lines).strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    print(f"\033[1;{self.program_color}mExiting...\033[0m")
                    break
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
        )

        session.start()
    except Exception as e:
        print(f"\033[1;31m[SESSION] Failed to start session: {str(e)}\033[0m")
        exit(1)

