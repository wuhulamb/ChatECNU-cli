# ECNU Chat Client

## 项目简介

ECNU Chat Client 是一个命令行交互工具，用于与华东师范大学的AI聊天模型(ecnu-max和ecnu-reasoner)进行交互。该工具提供Linux和Windows双版本支持。

## 功能特性

- 支持两种模型选择：ecnu-max (v3) 和 ecnu-reasoner (r1)
- 可上传文件作为对话上下文
- 支持自定义系统提示(prompt)
- 可调节温度参数(0-2)
- 彩色终端输出区分不同内容
- 自动维护对话历史长度

## 安装与配置

### 1. 环境要求

- Python 3.7+
- 安装依赖包：
  ```
  pip install openai python-dotenv
  ```

### 2. 配置文件

在脚本同目录下创建`.env`文件，内容为：
```
CHATECNU_API_KEY=您的API密钥
```

### 3. 提示文件

程序会自动根据模型选择加载对应的提示文件：
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
| `-m`, `--model` | 选择模型: `v3`(ecnu-max)或`r1`(ecnu-reasoner) | `v3` |
| `-t`, `--temperature` | 设置温度参数(0-2) | `v3`:0.3, `r1`:0.6 |
| `-f`, `--file` | 上传文本文件作为初始上下文 | 无 |
| `-p`, `--prompt-file` | 自定义系统提示文件 | 默认提示文件 |

### 发送文字

为了能~~复制粘贴~~输入多行文本，将发送键从回车改成了输入`EOF`（文件结束符）。输入文字后，需要先换到空行，再输入`EOF`。Unix/Linux按`Ctrl+D`直接提交，Windows按`Ctrl+Z`需要再按Enter提交。

### 使用示例

1. 使用默认模型(v3)启动：
   ```bash
   python main.py
   ```

2. 使用reasoner模型并上传文件：
   ```bash
   python main.py -m r1 -f example.txt
   ```

3. 自定义温度和提示：
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
   - 更长对话历史(15轮)

2. **ecnu-reasoner (r1)**:
   - 会显示推理过程
   - 默认温度: 0.6
   - 较短对话历史(10轮)
   - 输出包含"Think"和"Answer"部分

## 注意事项

1. 确保`.env`文件中配置了正确的API密钥
2. 程序所在目录要有`ecnu-v3.md`和`ecnu-r1.md`文件
3. 上传的文件必须是UTF-8编码的文本文件
4. 大温度值可能导致输出更加随机
5. 上传的文件内容会作为系统消息添加到对话中
6. Windows用户注意路径分隔符
