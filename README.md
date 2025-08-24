# ECNU Chat Client

一个跨平台的命令行客户端，用于与华东师范大学AI聊天模型交互，支持文本和图像输入。

## 功能特性

- 支持多平台：Linux和Windows版本
- 多模型选择：
  - `ecnu-max` (v3): 默认通用模型
  - `ecnu-reasoner` (r1): 推理增强模型（显示思考过程）
  - `ecnu-vl` (vl): 自动启用的视觉模型（当传入图片时）
- 交互式对话界面
- 可调节的温度参数
- 自定义系统提示词
- 文件上传与解析（支持文本文件）
- 图片内容理解（支持JPEG等常见格式）
- 彩色终端输出（支持Windows ANSI颜色）

## 文件结构

```text
.
├── main_linux.py        # Linux主程序
├── main_windows.py      # Windows主程序
├── .env.example         # 环境变量示例
├── ecnu-v3.md           # 默认系统提示词
└── ecnu-r1.md           # 推理模型提示词
```

## 系统要求

- Python 3.7+
- Windows 10+ 或 Linux
- 有效的API密钥（存储在.env文件中）

## 安装步骤

1. 克隆仓库或下载源代码
2. 安装依赖：
   ```
   pip install openai python-dotenv
   ```
3. 创建`.env`文件并添加API密钥：
   ```
   CHATECNU_API_KEY=your_api_key_here
   ```
4. 提示文件（必须）

   将项目中的两个提示文件一并下载下来，放在脚本同目录下，程序会自动根据模型选择加载对应的提示文件：
   - `ecnu-v3.md`：ecnu-max模型默认提示
   - `ecnu-r1.md`：ecnu-reasoner模型默认提示

## 使用方法

### 基本命令

```bash
python main.py [选项]
```

### 命令行选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `-h`, `--help` | 显示帮助信息并退出 | 无 |
| `-m`, `--model` | 选择模型(v3/r1) | v3 |
| `-t`, `--temperature` | 设置生成温度 | 模型默认值 |
| `-p`, `--prompt-file` | 自定义提示词文件 | 内置文件 |
| `-f`, `--files` | 上传文本文件 | 无 |
| `-i`, `--images` | 上传图片文件 | 无 |

### 交互控制

- **Linux**: 输入完成后按 `Ctrl+D` 提交
- **Windows**: 输入完成后按 `Ctrl+Z` 然后按 `Enter` 提交
- 输入 `exit` 或 `quit` 或按 `Ctrl+C` 退出程序

### 使用示例

1. 使用默认模型简单聊天：
   ```bash
   python main.py
   ```

2. 使用推理模型并上传文件：
   ```bash
   python main.py -m r1 -f document.txt
   ```

3. 分析图片内容：
   ```bash
   python main.py -i photo.jpg
   ```

4. 自定义温度和提示：
   ```bash
   python main.py -t 0.8 -p custom_prompt.md
   ```

## 版本说明

- **main_linux.py**:
  - 适配Linux系统
  - 输入多行内容后按`Ctrl+D`提交

- **main_indows.py**:
  - 适配Windows系统
  - 输入多行内容后按`Ctrl+Z`然后按`Enter`提交

## 模型说明

1. **ecnu-max (v3)**:
   - 默认模型
   - 默认温度: 0.3

2. **ecnu-reasoner (r1)**:
   - 会显示推理过程
   - 默认温度: 0.6
   - 输出包含"Think"和"Answer"部分

3. **ecnu-vl (vl)**:
   - 多模态模型
   - 默认温度: 0.01
   - 使用`-i`参数时强制使用该模型

## 注意事项

1. 确保`.env`文件中配置了正确的API密钥
2. 程序所在目录要有`ecnu-v3.md`和`ecnu-r1.md`文件
3. `-f`上传的文件必须是UTF-8编码的文本文件
4. 大温度值可能导致输出更加随机
5. Windows用户注意路径分隔符
