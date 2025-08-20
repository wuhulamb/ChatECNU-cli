# windows version
import os
import argparse
import ctypes
import base64
from openai import OpenAI
from dotenv import load_dotenv

# Windows-specific initialization for ANSI color support
if os.name == 'nt':
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# Get absolute path of current script
script_path = os.path.abspath(__file__)
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
    def __init__(self, model, temperature, system_prompt, file_paths, image_paths):
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

        if temperature:
            self.temperature = temperature
        else:
            self.temperature = self._get_model_temp(model)

        self.messages = [{"role": "system", "content": self.system_prompt}]

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
            system_prompt = os.path.normpath(system_prompt)  # Normalize path for Windows
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

    def add_file_contents(self, file_paths):
        """Add multiple file contents to conversation context"""
        for file_path in file_paths:
            file_path = os.path.normpath(file_path)  # Normalize path for Windows
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
            image_path = os.path.normpath(image_path)  # Normalize path for Windows
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

    def start(self):
        print(f"\033[1;{self.program_color}mECNU Chat Client (Type 'exit' to quit)\033[0m\n")
        print(f"\033[1;{self.program_color}mUsing model: {self.model} (Temperature: {self.temperature})\033[0m")
        print(f"\033[1;{self.program_color}mTip: Paste multi-line text and press Ctrl+Z + Enter to submit\033[0m")

        if self.file_paths:
            print(f"\033[1;33m{len(self.file_paths)} file(s) have been loaded. You can now ask questions about them.\033[0m")
        if self.image_paths:
            print(f"\033[1;33m{len(self.image_paths)} image(s) have been loaded. You can now ask questions about them.\033[0m")

        while True:
            try:
                print(f"\n\033[1;{self.user_color}mUser: (Input text then press Ctrl+Z + Enter to submit)\033[0m\n")
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
    parser.add_argument('-i', '--images', default=None, nargs='+',
                      help="Paths to image files for vision model interaction (multiple files allowed)")
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
            image_paths=args.images
        )

        session.start()
    except Exception as e:
        print(f"\033[1;31m[SESSION] Failed to start session: {str(e)}\033[0m")
        exit(1)
