# ECNU Chat Client

跨平台命令行客户端，用于与华东师范大学AI聊天模型交互，支持文本和图像输入。

## 功能特性

- **跨平台支持**：提供Linux和Windows两个版本
- **多模型选择**：
  - `ecnu-max` (v3): 默认通用模型，温度默认0.3
  - `ecnu-reasoner` (r1): 推理增强模型（显示思考过程），温度默认0.6
  - `ecnu-vl` (vl): 多模态视觉模型，自动启用（使用`-i`参数时）
- **交互功能**：
  - 交互式对话界面
  - 可调节温度参数
  - 自定义系统提示词
  - 文件上传与解析（文本文件）
  - 图片内容理解（JPEG等格式）
  - 对话历史保存与加载
  - 自动生成对话摘要作为文件名
- **终端优化**：
  - 彩色输出（支持Windows ANSI颜色）
  - 流式响应显示
  - 多行输入支持

## 系统要求

- Python 3.7+
- 依赖包：`openai`、`python-dotenv`
- 操作系统：Windows 10+ 或 Linux
- 有效的API密钥（需配置在.env文件中）

## 快速开始

1. **安装依赖**：
   ```bash
   pip install openai python-dotenv
   ```

2. **配置环境**：
   - 创建`.env`文件并添加API密钥：
     ```
     CHATECNU_API_KEY=your_api_key_here
     ```
   - 确保项目包含必要的配置文件：
     - `config.json` - 模型配置（必须）
     - `prompts/`文件夹 - 包含`ecnu-v3.md`和`ecnu-r1.md`提示词文件（必须）

3. **启动客户端**：
   ```bash
   # Linux
   python main_linux.py

   # Windows
   python main_windows.py
   ```

## 使用方法

### 命令行选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `-m`, `--model` | 选择模型(v3/r1) | v3 |
| `-t`, `--temperature` | 设置生成温度 | 模型默认值 |
| `-p`, `--prompt-file` | 自定义提示词文件 | 内置文件 |
| `-f`, `--files` | 上传文本文件（可多个） | 无 |
| `-i`, `--images` | 上传图片文件（可多个） | 无 |
| `-l`, `--load-chat` | 加载已保存的对话文件 | 无 |

### 交互控制

- **提交输入**：Linux按`Ctrl+D`，Windows按`Ctrl+Z`然后按`Enter`
- **退出程序**：输入`exit`、`quit`或`q`，或按`Ctrl+C`
- **保存对话**：输入`save`或`s`保存至`saved_chats`文件夹
- **清空输入**：输入`clear`或`c`

### 使用示例

```bash
# 使用推理模型分析文档
python main_linux.py -m r1 -f document.txt

# 使用视觉模型分析图片
python main_windows.py -i photo.jpg

# 加载之前对话并继续
python main_linux.py -l saved_chats/chat_20250901_123456_discussion.json
```

## 项目结构

```
.
├── chat_session.py      # 核心共享模块（ChatSession类）
├── main_linux.py        # Linux版本主程序
├── main_windows.py      # Windows版本主程序
├── config.json          # 配置文件
├── prompts/             # 提示词文件夹
│   ├── ecnu-v3.md       # ecnu-max模型提示词
│   └── ecnu-r1.md       # ecnu-reasoner模型提示词
└── saved_chats/         # 对话保存目录
    └── chat_*.json      # 保存的对话文件
```

## 模型说明

- **ecnu-max (v3)**: 默认通用模型，温度0.3
- **ecnu-reasoner (r1)**: 推理增强模型，显示思考过程，温度0.6
- **ecnu-vl (vl)**: 多模态视觉模型，温度0.01，上传图片时自动启用

## 技术架构

项目采用模块化设计，将95%的通用功能集中在`chat_session.py`中：

- **核心模块**：配置管理、API调用、文件处理、对话管理、错误处理
- **平台适配**：Linux使用readline支持历史命令，Windows内置ANSI颜色支持

这种设计提高了代码复用性，便于维护和扩展。

## 注意事项

- 确保`.env`文件配置正确的API密钥
- `config.json`和提示词文件必须存在
- 上传的文本文件需为UTF-8编码
- 大温度值会增加输出随机性
- 过大图像文件可能无法处理

## 配置文件示例

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
  },
  "colors": {
    "user": "32",
    "assistant": "34",
    "reasoning": "33"
  }
}
```

配置文件中可修改默认模型、温度参数和颜色设置。
