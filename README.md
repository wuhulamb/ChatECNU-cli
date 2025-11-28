# ChatECNU CLI

跨平台命令行客户端，用于与华东师范大学AI聊天模型交互，支持文本和图像输入、系统命令执行等功能。

## 🚀 功能特性

- **统一跨平台架构**：单一入口`main.py`自动适配Linux/Windows平台
- **多模型支持**：
  - `ecnu-max` (v3): 默认通用模型，温度0.3
  - `ecnu-reasoner` (r1): 推理增强模型（显示思考过程），温度0.6
  - `ecnu-vl` (vl): 多模态视觉模型，自动启用（使用`-i`参数时）
- **运行模式**：
  - **交互模式**：多轮对话体验
  - **非交互模式**：`-P`参数支持脚本化使用
- **增强功能**：
  - 文件上传与内容分析（文本文件）
  - 图片内容理解（JPEG等格式）
  - **安全命令执行**：支持bash命令执行（需启用）
  - 对话历史保存与加载
  - 自动生成对话摘要作为文件名

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
| `-m`, `--model` | 选择模型(v3/r1) | v3 |
| `-t`, `--temperature` | 设置生成温度 | 模型默认值 |
| `-p`, `--prompt-file` | 自定义提示词文件 | 内置文件 |
| `-f`, `--files` | 上传文本文件（可多个） | 无 |
| `-i`, `--images` | 上传图片文件（可多个） | 无 |
| `-l`, `--load-chat` | 加载已保存的对话文件 | 无 |
| `-P`, `--print` | 非交互模式输入文本 | 无 |

### 交互控制

- **提交输入**：Linux按`Ctrl+D`，Windows按`Ctrl+Z`然后按`Enter`
- **退出程序**：输入`q`，或按`Ctrl+C`
- **保存对话**：输入`s`保存至`saved_chats`文件夹
- **清空输入**：输入或`c`
- **命令模式**：输入`bash on`启用，`bash off`禁用

## 💡 使用示例

### 非交互模式（脚本友好）

```bash
# 基础用法：直接提问
python main.py -P "帮我解释一下人工智能的基本概念"

# 使用推理模型
python main.py -m r1 -P "请推理解决这个数学问题..."

# 分析文档内容
python main.py -f document.txt -P "总结这个文档的主要观点"

# 图片内容分析
python main.py -i photo.jpg -P "描述图片中的内容"

# 继续历史对话
python main.py -l saved_chats/chat_20250901_123456.json -P "继续刚才的话题"
```

### 交互模式

```bash
# 使用推理模型分析文档
python main.py -m r1 -f document.txt

# 使用视觉模型分析图片
python main.py -i photo.jpg

# 启用命令执行模式
python main.py
# 然后在对话中输入：bash on
```

### 命令执行功能

启用bash命令模式后，可以：

1. **直接执行命令**：输入`!ls`、`!pwd`等
2. **AI推荐命令**：询问AI生成命令建议，选择执行
3. **安全验证**：自动阻止危险命令，需要用户确认

```bash
# 启用命令模式
bash on

# 执行系统命令（带确认）
!ls -la
!cat README.md
!find . -name "*.py"
```

## 🏗️ 项目架构

重构后的统一架构大幅提升了代码复用性和维护性：

### 核心模块

- **`main.py`**：统一入口，自动平台检测和处理器选择
- **`chat_session.py`**：核心会话管理（95%代码复用）
- **`command_processor.py`**：安全命令执行系统
- **`platform_handlers/`**：平台特定输入处理
  - `linux.py`：Linux处理器（readline支持）
  - `windows.py`：Windows处理器（ANSI颜色支持）
  - `common.py`：通用处理器

### 项目结构

```
ChatECNU-cli/
├── main.py                 # 统一入口点
├── chat_session.py         # 核心会话管理
├── command_processor.py    # 命令执行系统
├── config.py               # 配置管理
├── config.json             # 配置文件
├── platform_handlers/      # 平台处理器
│   ├── linux.py
│   ├── windows.py
│   └── common.py
├── prompts/                # 提示词模板
│   ├── ecnu-v3.md
│   ├── ecnu-r1.md
│   └── ecnu-bash.md
└── saved_chats/            # 对话保存目录
    └── chat_*.json
```

## 🔧 配置说明

### 模型配置

```json
{
  "model_name": {
    "v3": "ecnu-max",
    "r1": "ecnu-reasoner",
    "vl": "ecnu-vl",
    "default": "ecnu-max"
  },
  "temperature_defaults": {
    "ecnu-reasoner": 0.6,
    "ecnu-max": 0.3,
    "ecnu-vl": 0.01,
    "default": 0.3
  }
}
```

### 命令执行安全配置（Linux）

```json
"bash_commands_linux": {
  "enabled": false,
  "command_prefix": "!",
  "allowed_commands": ["ls", "pwd", "cat", "grep", "find", "echo", "mkdir", "cd"],
  "dangerous_commands": ["rm", "dd", "chmod", "chown", "mv", "cp", "sudo"],
  "timeout_seconds": 30,
  "max_output_length": 10000,
  "require_confirmation": true
}
```

## 🌟 高级功能

### 自动模型切换
- 上传图片时自动启用视觉模型
- 加载含图像的对话时自动适配模型

### 智能提示词切换
- 启用命令模式时自动使用`ecnu-bash.md`专用提示词
- 支持运行时动态切换系统提示词

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
- ✅ 增强命令执行：安全bash命令支持
- ✅ 模块化设计：平台处理器分离
- ✅ 非交互模式：脚本友好输出

### v1.0 (初始版本)
- 基础对话功能
- 文件/图片上传
- 双平台独立入口

---

**ChatECNU CLI** - 让AI交互更简单、更安全、更强大！
