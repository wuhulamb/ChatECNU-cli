# ChatECNU CLI

跨平台命令行客户端，用于与华东师范大学AI聊天模型交互，支持文本和图像输入、系统命令执行等功能。

## 🚀 功能特性

- **统一跨平台架构**：单一入口`main.py`自动适配Linux/Windows平台
- **多模型支持**：
  - `ecnu-max`: 默认通用模型，温度0.3
  - `ecnu-reasoner`: 推理增强模型（显示思考过程），温度0.6
  - `ecnu-vl`: 多模态视觉模型，自动启用（使用`-i`参数时）
  - `ecnu-turbo`: 快速响应模型
  - 支持DeepSeek等第三方模型
- **运行模式**：
  - **交互模式**：多轮对话体验
  - **非交互模式**：`-s`参数支持脚本化使用
  - **对话查看模式**：`-P`参数查看已保存的对话
- **增强功能**：
  - 文件上传与内容分析（文本文件）
  - 图片内容理解（JPEG等格式）
  - 对话历史保存与加载
  - 自动生成对话摘要作为文件名
  - 命令执行

## 📋 系统要求

- Python 3.7+
- 必需依赖包：`openai`、`python-dotenv`
- 操作系统：Windows 10+ 或 Linux
- 有效的ECNU API密钥（需配置在.env文件中）

## ⚡ 快速开始

### 1. 安装依赖
```bash
pip install openai python-dotenv
```

### 2. 配置环境
创建`.env`文件并添加API密钥：
```bash
CHATECNU_API_KEY=your_api_key_here
DEEPSEEK_API_KEY=your_api_key_here
OTHER_PROVIDER_API_KEY=your_api_key_here
```

### 3. 启动客户端
```bash
# 所有平台统一命令
python main.py
```

## 🎯 使用方法

### 命令行选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `-m`, `--model` | 选择模型（格式：provider:model 或 model） | ecnu-max |
| `-t`, `--temperature` | 设置生成温度 | 模型默认值 |
| `-p`, `--prompt-file` | 自定义提示词文件路径 | 内置文件 |
| `-f`, `--files` | 上传文本文件（可多个） | 无 |
| `-i`, `--images` | 上传图片文件（可多个） | 无 |
| `-l`, `--load-chat` | 加载已保存的对话文件 | 无 |
| `-P`, `--print-chat` | 查看已保存的对话文件内容 | 无 |
| `-s`, `--silent` | 非交互模式输入文本 | 无 |

### 交互控制

- **提交输入**：Linux按`Ctrl+D`，Windows按`Ctrl+Z`然后按`Enter`
- **退出程序**：输入`q`，或按`Ctrl+C`
- **保存对话**：输入`s`保存至`saved_chats`文件夹
- **清空输入**：输入或`c`
- **执行命令**：输入`!<command>`执行系统命令

## 💡 使用示例

### 非交互模式（脚本友好）

```bash
# 基础用法：直接提问
python main.py -s "帮我解释一下人工智能的基本概念"

# 使用推理模型
python main.py -m ecnu-reasoner -s "请推理解决这个数学问题..."

# 分析文档内容
python main.py -f document.txt -s "总结这个文档的主要观点"

# 图片内容分析
python main.py -i photo.jpg -s "描述图片中的内容"

# 继续历史对话
python main.py -l saved_chats/chat_20250901_123456.json -s "继续刚才的话题"
```

### 交互模式

```bash
# 使用推理模型分析文档
python main.py -m ecnu-reasoner -f document.txt

# 使用视觉模型分析图片
python main.py -i photo.jpg

# 加载历史对话继续聊天
python main.py -l saved_chats/chat_20250101_120000_conversation.json
```

### 查看已保存的对话

```bash
# 查看保存的对话文件
python main.py -P saved_chats/chat_20250101_120000_conversation.json
```

### 命令执行功能

**直接执行命令**：输入`!ls`、`!pwd`等

```bash
# 执行系统命令
!ls -la
!cat README.md
!find . -name "*.py"
```

## 🏗️ 项目架构

重构后的统一架构大幅提升了代码复用性和维护性：

### 核心模块

- **`main.py`**：统一入口，自动平台检测和处理器选择
- **`chat.py`**：核心会话管理（ChatSession类）
- **`utils.py`**：工具函数集合（文件处理、命令执行、配置加载等）
- **`linux.py`**：Linux平台输入处理器
- **`windows.py`**：Windows平台输入处理器
- **`config.json`**：配置文件

### 项目结构

```
ChatECNU-cli/
├── main.py                 # 统一入口点
├── chat.py                 # 核心会话管理（ChatSession类）
├── utils.py                # 工具函数
├── config.json             # 配置文件
├── linux.py                # Linux平台处理器
├── windows.py              # Windows平台处理器
├── prompts/                # 提示词模板
│   ├── ecnu-v3.md
│   └── ecnu-r1.md
├── saved_chats/            # 对话保存目录
│   └── chat_*.json
└── .env                    # 环境变量文件（需手动创建）
```

### 函数调用关系

```
main.py:main()
├── load_config() [utils.py]
├── get_common_parser() [utils.py]
├── initialize_openai_client() [utils.py]
│   └── load_env_file() [utils.py]
├── ChatSession() [chat.py]
│   ├── _get_model_temp()
│   ├── _get_system_prompt()
│   ├── add_file_contents() [utils.py]
│   ├── add_image_contents() [utils.py]
│   └── load_conversation() [可选]
│       └── has_image_content() [utils.py]
├── session.start() [chat.py]
│   ├── add_user_message() [chat.py]
│   ├── generate_assistant_response() 或 generate_silent_response() [chat.py]
│   ├── save_conversation() [chat.py]
│   │   └── generate_summary() [utils.py]
│   └── process_user_command() [utils.py] [当输入命令时]
│       ├── extract_command() [utils.py]
│       ├── validate_command_safety() [utils.py]
│       ├── execute_command() [utils.py]
│       ├── format_command_output() [utils.py]
│       └── add_command_result_to_messages() [utils.py] [可选]
└── print_conversation() [utils.py] [当使用 --print-chat 参数时]
```

## 🔧 配置说明

### 模型配置（config.json）

支持多模型提供商配置：
```json
{
  "model_providers": {
    "ecnu": {
      "base_url": "https://chat.ecnu.edu.cn/open/api/v1",
      "api_key_env": "CHATECNU_API_KEY",
      "vision_model": "ecnu-vl",
      "generate_summary_model": "ecnu-turbo",
      "models": {
        "ecnu-max": {
          "prompt_defaults": "ecnu-v3.md",
          "temperature_defaults": 0.3
        },
        "ecnu-reasoner": {
          "prompt_defaults": "ecnu-r1.md",
          "temperature_defaults": 0.6
        },
        "ecnu-vl": {
          "prompt_defaults": "ecnu-v3.md",
          "temperature_defaults": 0.01
        },
        "ecnu-turbo": {
          "prompt_defaults": "ecnu-v3.md",
          "temperature_defaults": 0.3
        }
      }
    },
    "deepseek": {
      "base_url": "https://api.deepseek.com",
      "api_key_env": "DEEPSEEK_API_KEY",
      "models": {
        "deepseek-chat": {
          "prompt_defaults": "ecnu-v3.md",
          "temperature_defaults": 0.3
        },
        "deepseek-reasoner": {
          "prompt_defaults": "ecnu-r1.md",
          "temperature_defaults": 0.6
        }
      }
    }
  }
}
```

### 命令执行安全配置（Linux）

```json
"bash_commands_linux": {
  "command_prefix": "!",
  "dangerous_commands": ["rm", "dd", "chmod", "chown", "mv", "cp", "sudo"],
  "timeout_seconds": 30,
  "max_output_length": 10000,
}
```

## 🌟 高级功能

### 自动模型切换
- 上传图片时自动启用视觉模型

### 对话持久化
- JSON格式保存完整对话历史
- 自动生成描述性文件名
- 支持加载和继续任意历史对话

## 📝 注意事项

- 确保`.env`文件配置正确的API密钥
- `config.json`和提示词文件必须存在
- 上传的文本文件需为UTF-8编码
- 大温度值会增加输出随机性
- 过大图像文件可能无法处理
- 命令执行功能默认禁用，需手动启用

## 🔄 版本历史

### v2.0 (重构版本)
- ✅ 统一架构：单一入口代替平台特定文件
- ✅ 增强命令执行：bash命令支持
- ✅ 模块化设计：平台处理器分离
- ✅ 非交互模式：脚本友好输出
- ✅ 多模型支持：可自定义openAI接口兼容提供商

### v1.0 (初始版本)
- 基础对话功能
- 文件/图片上传
- 双平台独立入口

---

**ChatECNU CLI** - 让AI交互更简单、更安全、更强大！
