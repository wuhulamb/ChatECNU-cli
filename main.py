#!/home/xu/python/code/bin/python
import os
import readline
import argparse
from openai import OpenAI
from dotenv import load_dotenv

# 获取当前脚本的绝对路径（如果是符号链接，解析真实路径）
script_path = os.path.realpath(__file__)
script_dir = os.path.dirname(script_path)

# 拼接 .env 文件的路径
env_path = os.path.join(script_dir, ".env")

# 显式加载指定路径的 .env
load_dotenv(dotenv_path=env_path)

class ChatSession:
    def __init__(self, model, temperature, system_prompt, max_history=None):
        self.user_color = "32"  # 绿色
        self.assistant_color = "34"  # 蓝色
        self.model = self._get_model_name(model)  # 转换为实际模型名称
        self.temperature = temperature  # 使用传入的温度参数
        self.system_prompt = system_prompt
        # 根据模型类型设置历史记录长度
        if max_history is None:
            self.max_history = 10 if "reasoner" in self.model else 15
        else:
            self.max_history = max_history
        self.messages = [
            {"role": "system", "content": self.system_prompt}
        ]

    def _get_model_name(self, model_flag):
        """将参数转换为实际模型名称"""
        model_mapping = {
            "r1": "ecnu-reasoner",
            "v3": "ecnu-max"
        }
        return model_mapping.get(model_flag, "ecnu-max")

    def _trim_history(self):
        # ... 保持原有修剪逻辑不变 ...
        if len(self.messages) > self.max_history * 2 + 1:
            self.messages = [self.messages[0]] + self.messages[-self.max_history * 2:]

    def add_user_message(self, content):
        """添加用户消息到对话历史"""
        self.messages.append({"role": "user", "content": content})

    def generate_assistant_response(self):
        """生成助手响应并处理流式输出"""
        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                stream=True,
                temperature=self.temperature,
            )

            full_response = []
            print(f"\n\033[1;{self.assistant_color}mAssistant: \033[0m\n", end="", flush=True)
            for chunk in stream:
                if "reasoner" in self.model and chunk.choices[0].delta.reasoning_content:
                    reasoning_content = chunk.choices[0].delta.reasoning_content
                    print(reasoning_content, end="", flush=True)

                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    print(content, end="", flush=True)
                    full_response.append(content)
            print()

            self.messages.append({
                "role": "assistant",
                "content": "".join(full_response)
            })

            self._trim_history()
            return True
        except Exception as e:
            print(f"\n\033[1;31m\nError occurred: {str(e)}\033[0m")
            return False

    def start(self):
        print("\033[1;36mECNU Chat Client (Enter 'exit' to quit)\033[0m")
        print(f"\n\033[1;36mUsing model: {self.model} (Temperature: {self.temperature})\033[0m")
        
        while True:
            try:
                user_input = input(f"\n\033[1;{self.user_color}mUser: \033[0m\n").strip()
                
                if user_input.lower() in ['exit', 'quit']:
                    print("\033[1;33m\nExit ...\033[0m")
                    break
                if not user_input:
                    continue

                self.add_user_message(user_input)
                if not self.generate_assistant_response():
                    break

            except KeyboardInterrupt:
                print("\n\033[1;33m\nSession terminated by user.\033[0m")
                break

def load_prompt_file(model_flag, custom_path=None):
    """加载提示词文件"""
    if custom_path:
        # 如果提供了自定义路径，将其转换为绝对路径
        if not os.path.isabs(custom_path):
            custom_path = os.path.join(os.getcwd(), custom_path)
        if not os.path.exists(custom_path):
            raise FileNotFoundError(f"Prompt file not found: {custom_path}")
        prompt_path = custom_path
    else:
        default_file = "deepseek-r1.md" if model_flag == "r1" else "deepseek-v3.md"
        prompt_path = os.path.join(script_dir, default_file)

    with open(prompt_path, "r") as f:
        return f.read()

if __name__ == "__main__":
    # 配置命令行参数解析
    parser = argparse.ArgumentParser(description="A CLI client for interacting with DeepSeek's AI chat models.")
    parser.add_argument('-m', '--model',
                      default='v3',
                      choices=['v3', 'r1'],
                      help="模型选择：v3=ecnu-max (default), r1=ecnu-reasoner")
    # 提示文件参数
    parser.add_argument('-p', '--prompt-file',
                      default=None,
                      help="自定义系统提示词文件路径（未指定时使用模型默认）")
    parser.add_argument('-t', '--temperature',
                      type=float,
                      default=None,
                      help="温度参数：(默认: v3=0.3, r1=0.6)")

    # 添加文件参数
    parser.add_argument('-f', '--file',
                      default=None,
                      help="Path to a text file to upload as initial context")

    args = parser.parse_args()

    # 加载提示词内容
    try:
        system_prompt = load_prompt_file(args.model, args.prompt_file)
    except FileNotFoundError as e:
        print(f"\033[1;31mError: {str(e)}\033[0m")
        exit(1)

    # 设置默认温度值
    if args.temperature is None:
        args.temperature = 0.6 if args.model == 'r1' else 0.3

    # 处理文件上传
    if args.file:
        try:
            with open(args.file, 'r') as f:
                file_content = f.read()
            print(f"\033[1;32m\nUploaded file content from {args.file}:\033[0m")
            print(file_content)
            session.add_user_message(f"Here is the content of my file:\n{file_content}")
            session.generate_assistant_response()
        except Exception as e:
            print(f"\033[1;31mError reading file: {str(e)}\033[0m")
            exit(1)

    # 初始化客户端和会话
    client = OpenAI(
        api_key=os.getenv("CHATECNU_API_KEY"),
        base_url="https://chat.ecnu.edu.cn/open/api/v1",
    )

    session = ChatSession(
        model=args.model,
        temperature=args.temperature,
        system_prompt=system_prompt
    )

    session.start()
