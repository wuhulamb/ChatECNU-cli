#!/usr/bin/env python3
"""
ChatECNU CLI - Command Processor Module
Handles system command execution (bash, powershell, etc.)
Extracted from chat_session.py for better separation of concerns.
"""

import os
import re
import subprocess
import sys


class CommandProcessor:
    """Handles system command execution with safety controls."""

    def __init__(self, script_dir):
        """Initialize command processor with script directory."""
        self.script_dir = script_dir
        self.config = {}
        self.bash_config = {}
        self.enabled = False

        # Initialize default colors
        self.user_color = "32"
        self.program_color = "36"
        self.assistant_color = "34"
        self.reasoning_color = "33"

    def is_command_input(self, input_text):
        """Check if input is a direct command (starts with '!')."""
        prefix = self.bash_config.get("command_prefix", "!")
        return input_text.strip().startswith(prefix)

    def is_ai_generated_command(self, response_text):
        """Check if AI response contains bash commands in special format."""
        if not self.bash_config.get("enabled", False):
            return []

        # Look for commands between [BASH_COMMAND_START] and [BASH_COMMAND_END]
        commands = []
        pattern = r'\[BASH_COMMAND_START\](.*?)\[BASH_COMMAND_END\]'
        matches = re.findall(pattern, response_text, re.DOTALL)

        for match in matches:
            # Extract each command line
            for line in match.strip().split('\n'):
                cmd = line.strip()
                if cmd and not cmd.startswith('#') and cmd not in commands:
                    commands.append(cmd)

        return commands

    def process_ai_commands(self, ai_response, messages):
        """Process AI-generated commands and handle user selection."""
        if not self.enabled:
            return False

        ai_commands = self.is_ai_generated_command(ai_response)
        if not ai_commands:
            return False

        print(f"\033[1;{self.program_color}m[BASH] AI provided {len(ai_commands)} command suggestions\033[0m")
        print(f"\033[1;{self.program_color}m[BASH] Please select a command to execute (enter number 1-{len(ai_commands)}, or 0 to skip): \033[0m")

        for i, cmd in enumerate(ai_commands, 1):
            print(f"\033[1;{self.program_color}mBash {i}: {cmd}\033[0m")

        try:
            choice = input("\033[1;32mChoice: \033[0m").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(ai_commands):
                cmd = ai_commands[int(choice) - 1]
                if self.validate_command_safety(cmd):
                    result = self.execute_command(cmd)
                    if result:
                        self.add_command_result_to_messages(result, messages)
                        return True
        except (KeyboardInterrupt, EOFError):
            print(f"\033[1;{self.program_color}m[BASH] Command execution skipped\033[0m")

        return False

    def extract_command(self, input_text):
        """Extract the actual command from input (remove prefix)."""
        prefix = self.bash_config.get("command_prefix", "!")
        return input_text.strip()[len(prefix):].strip()

    def validate_command_safety(self, command):
        """Validate if the command is safe to execute."""
        # Check if command is empty
        if not command.strip():
            return False

        # Extract the first word (command name)
        cmd_name = command.strip().split()[0].lower()

        # Check against dangerous commands
        dangerous_commands = self.bash_config.get("dangerous_commands", [])
        if cmd_name in dangerous_commands:
            print(f"\033[1;31m[BASH] Dangerous command blocked: {cmd_name}\033[0m")
            return False

        # Check against allowed commands
        allowed_commands = self.bash_config.get("allowed_commands", [])
        if allowed_commands and cmd_name not in allowed_commands:
            print(f"\033[1;31m[BASH] Command not in allowed list: {cmd_name}\033[0m")
            return False

        return True

    def execute_command(self, command):
        """Safely execute a command and return the execution result."""
        timeout_seconds = self.bash_config.get("timeout_seconds", 30)
        max_output_length = self.bash_config.get("max_output_length", 10000)

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(timeout=timeout_seconds)
            return_code = process.returncode

            # Apply output length limits
            if len(stdout) > max_output_length:
                stdout = stdout[:max_output_length] + "\n[Output truncated]"

            if len(stderr) > max_output_length:
                stderr = stderr[:max_output_length] + "\n[Error output truncated]"

            # Format and display output
            self.format_command_output(command, stdout, stderr, return_code)

            # Return execution result
            return {
                "command": command,
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code
            }

        except subprocess.TimeoutExpired:
            print(f"\033[1;31m[BASH] Command timed out after {timeout_seconds} seconds\033[0m")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            return {
                "command": command,
                "stdout": "",
                "stderr": f"Command timed out after {timeout_seconds} seconds",
                "return_code": -1
            }
        except Exception as e:
            print(f"\033[1;31m[BASH] Command execution failed: {str(e)}\033[0m")
            return {
                "command": command,
                "stdout": "",
                "stderr": f"Command execution failed: {str(e)}",
                "return_code": -1
            }

    def format_command_output(self, command, stdout, stderr, return_code):
        """Format and display command execution results."""
        print(f"\033[1;{self.program_color}m[BASH] Command: {command}\033[0m")
        print(f"\033[1;{self.program_color}m[BASH] Return code: {return_code}\033[0m")

        if stdout:
            print(f"\033[1;32m[BASH] Output:\033[0m")
            print(stdout)

        if stderr:
            print(f"\033[1;31m[BASH] Errors:\033[0m")
            print(stderr)

        if return_code == 0 and not stdout and not stderr:
            print(f"\033[1;33m[BASH] Command completed successfully (no output)\033[0m")

    def add_command_result_to_messages(self, result, messages):
        """Add command execution result to messages as context."""
        command = result["command"]
        return_code = result["return_code"]
        stdout = result["stdout"]
        stderr = result["stderr"]

        # Create a formatted message with the command and its result
        bash_result_message = f"\n[System Command Executed]\n"
        bash_result_message += f"Command: {command}\n"
        bash_result_message += f"Exit Code: {return_code}\n"

        if stdout:
            bash_result_message += f"Output:\n{stdout}\n"

        if stderr:
            bash_result_message += f"Errors:\n{stderr}\n"

        # Add as a user message to provide context to AI
        messages.append({
            "role": "user",
            "content": bash_result_message
        })

    def toggle_mode(self, enable, reload_callback=None):
        """Enable or disable command execution mode."""
        self.enabled = enable
        self.bash_config["enabled"] = enable

        status = "enabled" if enable else "disabled"
        print(f"\033[1;{self.program_color}m[BASH] Command mode\033[0m \033[1;33m{status}\033[0m")

        # 调用回调函数重载提示词
        if reload_callback:
            reload_callback()

    def process_user_command(self, user_input, messages):
        """Process a user command and update messages if executed."""
        if not self.enabled:
            print(f"\033[1;33m[WARN] Command detected but execution is currently disabled (use 'bash on' to enable)\033[0m")
            return True

        command = self.extract_command(user_input)
        if self.validate_command_safety(command):
            # Execute command first (existing pre-execution confirmation still applies)
            result = self.execute_command(command)
            if result:
                # Add post-execution confirmation for adding results to messages
                print(f"\033[1;{self.program_color}m[BASH] Add command results to conversation? (Y/n): \033[0m", end="")
                try:
                    response = input().strip().lower()
                    if response in ['', 'y', 'yes']:
                        self.add_command_result_to_messages(result, messages)
                        print(f"\033[1;32m[BASH] Command results added to conversation\033[0m")
                    else:
                        print(f"\033[1;33m[BASH] Command results not added to conversation\033[0m")
                except (KeyboardInterrupt, EOFError):
                    print(f"\033[1;{self.program_color}m[BASH] Command results not added to conversation\033[0m")
                return True
        return True
