#!/home/xu/python/code/bin/python
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
    def __init__(self, model, temperature, system_prompt, max_history=None):
        self.user_color = "32"  # Green
        self.program_color = "36"  # Cyan
        self.assistant_color = "34"  # Blue
        self.reasoning_color = "33"  # Yellow
        self.model = self._get_model_name(model)
        self.temperature = temperature
        self.system_prompt = system_prompt
        if max_history is None:
            self.max_history = 10 if "reasoner" in self.model else 15
        else:
            self.max_history = max_history
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _get_model_name(self, model_flag):
        """Convert flag to actual model name"""
        model_mapping = {
            "r1": "ecnu-reasoner",
            "v3": "ecnu-max"
        }
        return model_mapping.get(model_flag, "ecnu-max")

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

            # 添加推理过程标识
            reasoning_started = False

            for chunk in stream:
                if "reasoner" in self.model and chunk.choices[0].delta.reasoning_content:
                    reasoning_content = chunk.choices[0].delta.reasoning_content

                    # 首次出现思考内容时添加前缀和分隔线
                    if not reasoning_started:
                        print(f"\033[1;{self.assistant_color}m{'='*30} Think {'='*30}\033[0m", flush=True)
                        print(f"\033[1;{self.reasoning_color}m", end="", flush=True)
                        reasoning_started = True

                    print(reasoning_content, end="", flush=True)

                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content

                    # 在思考结束后添加分隔线
                    if reasoning_started:
                        print("\033[0m")  # 结束思考颜色
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

    def add_file_content(self, file_path):
        """Add file content to conversation context"""
        if not os.path.exists(file_path):
            print(f"\033[1;31m[FILE] File not found: {file_path}\033[0m")
            return False

        try:
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:
                print(f"\033[1;31m[FILE] File too large (>10MB): {file_path}\033[0m")
                return False

            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()

            if not file_content.strip():
                print(f"\033[1;33m[WARNING] Empty file: {file_path}\033[0m")
                return False

            self.messages.append({
                "role": "system",
                "content": f"User has uploaded a file '{os.path.basename(file_path)}'. Here is its content:\n{file_content}"
            })
            return True

        except UnicodeDecodeError:
            print(f"\033[1;31m[FILE] Not a UTF-8 encoded file: {file_path}\033[0m")
            return False
        except PermissionError:
            print(f"\033[1;31m[FILE] Permission denied: {file_path}\033[0m")
            return False
        except Exception as e:
            print(f"\033[1;31m[FILE] Error reading file: {str(e)}\033[0m")
            return False

    def start(self, initial_file=None):
        print(f"\033[1;{self.program_color}mECNU Chat Client (Type 'exit' to quit)\033[0m\n")
        print(f"\033[1;{self.program_color}mUsing model: {self.model} (Temperature: {self.temperature})\033[0m")
        print(f"\033[1;{self.program_color}mTip: Paste multi-line text and press Ctrl+D to submit\033[0m")

        if initial_file:
            print(f"\033[1;33mFile content has been loaded. You can now ask questions about it.\033[0m")

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

def load_prompt_file(model_flag, custom_path=None):
    """Load prompt file"""
    if custom_path:
        if not os.path.isabs(custom_path):
            custom_path = os.path.join(os.getcwd(), custom_path)
        if not os.path.exists(custom_path):
            raise FileNotFoundError(f"Prompt file not found: {custom_path}")
        prompt_path = custom_path
    else:
        default_file = "deepseek-r1.md" if model_flag == "r1" else "deepseek-v3.md"
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A CLI client for interacting with ECNU's AI chat models.")
    parser.add_argument('-m', '--model', default='v3', choices=['v3', 'r1'],
                      help="Model selection: v3=ecnu-max (default), r1=ecnu-reasoner")
    parser.add_argument('-p', '--prompt-file', default=None,
                      help="Custom system prompt file path")
    parser.add_argument('-t', '--temperature', type=float, default=None,
                      help="Temperature parameter (default: v3=0.3, r1=0.6)")
    parser.add_argument('-f', '--file', default=None,
                      help="Path to text file to upload as initial context")

    args = parser.parse_args()

    if args.temperature is not None and not (0 <= args.temperature <= 2):
        print("\033[1;31m[ARG] Temperature must be between 0 and 2\033[0m")
        exit(1)

    try:
        system_prompt = load_prompt_file(args.model, args.prompt_file)
    except Exception as e:
        print(f"\033[1;31m[STARTUP] {str(e)}\033[0m")
        exit(1)

    if args.temperature is None:
        args.temperature = 0.6 if args.model == 'r1' else 0.3

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

    session = ChatSession(
        model=args.model,
        temperature=args.temperature,
        system_prompt=system_prompt
    )

    if args.file and not session.add_file_content(args.file):
        exit(1)

    session.start(initial_file=args.file)
