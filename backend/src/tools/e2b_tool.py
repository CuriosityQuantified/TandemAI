"""
E2B Code Execution Tool for ATLAS Analysis Agents
Provides safe sandboxed code execution capabilities using E2B API
"""

import os
import time
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging
import traceback as tb

try:
    from e2b_code_interpreter import CodeInterpreter, Result
except ImportError:
    CodeInterpreter = None
    Result = None

from ..agui.tool_events import broadcast_tool_call

logger = logging.getLogger(__name__)


class E2BTool:
    """Wrapper for E2B Code Interpreter with enhanced error handling and monitoring."""

    def __init__(self):
        """Initialize E2B client with API key from environment."""
        self.api_key = os.getenv('E2B_API_KEY')

        if not self.api_key:
            logger.warning("E2B_API_KEY not found in environment")
            self.client = None
        elif not CodeInterpreter:
            logger.error("e2b-code-interpreter package not installed")
            self.client = None
        else:
            logger.info("E2B tool initialized with API key")

    def _create_sandbox(self, timeout: int = 30) -> Optional[CodeInterpreter]:
        """Create a new E2B sandbox instance."""
        if not self.api_key or not CodeInterpreter:
            return None

        try:
            sandbox = CodeInterpreter(api_key=self.api_key)
            return sandbox
        except Exception as e:
            logger.error(f"Failed to create E2B sandbox: {e}")
            return None

    def _format_result(self,
                      result: Any,
                      language: str,
                      execution_time: float,
                      memory_usage: Optional[float] = None) -> Dict[str, Any]:
        """Format execution result into standardized dictionary."""
        formatted = {
            "status": "success",
            "language": language,
            "execution_time": execution_time,
            "timestamp": datetime.now().isoformat()
        }

        if result:
            # Handle E2B Result object
            if hasattr(result, 'text'):
                formatted["stdout"] = result.text or ""
            if hasattr(result, 'error'):
                formatted["stderr"] = result.error or ""
            if hasattr(result, 'result'):
                formatted["return_value"] = str(result.result) if result.result else None

            # Add any visualizations or data
            if hasattr(result, 'data'):
                formatted["data"] = result.data
            if hasattr(result, 'html'):
                formatted["html"] = result.html
            if hasattr(result, 'latex'):
                formatted["latex"] = result.latex

        if memory_usage:
            formatted["memory_usage_mb"] = memory_usage

        return formatted

    @broadcast_tool_call("e2b_execute_python", capture_result=True, capture_params=True)
    def execute_python(self,
                      code: str,
                      timeout: int = 30,
                      capture_plots: bool = True,
                      task_id: str = "default") -> Dict[str, Any]:
        """
        Execute Python code in E2B sandbox.

        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
            capture_plots: Whether to capture matplotlib plots
            task_id: Task identifier for event broadcasting

        Returns:
            Dictionary with execution results including stdout, stderr, and return value
        """
        if not self.api_key or not CodeInterpreter:
            return {
                "status": "error",
                "error": "E2B not configured or not installed",
                "language": "python"
            }

        sandbox = None
        start_time = time.time()

        try:
            logger.info(f"Executing Python code in E2B sandbox (timeout: {timeout}s)")

            # Create sandbox
            sandbox = self._create_sandbox(timeout)
            if not sandbox:
                raise Exception("Failed to create sandbox")

            # Add imports for common data science libraries
            setup_code = """
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import math
import statistics
import datetime
from collections import defaultdict, Counter
"""
            if capture_plots:
                setup_code += "\nplt.ion()  # Enable interactive plotting"

            # Execute setup silently
            sandbox.notebook.exec_cell(setup_code)

            # Execute the actual code
            result = sandbox.notebook.exec_cell(code)

            execution_time = time.time() - start_time

            # Format the result
            formatted_result = self._format_result(
                result,
                "python",
                execution_time
            )

            # Capture any generated plots
            if capture_plots and hasattr(result, 'display_data'):
                formatted_result["plots"] = result.display_data

            logger.info(f"Python code executed successfully in {execution_time:.2f}s")
            return formatted_result

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = str(e)
            stack_trace = tb.format_exc()

            logger.error(f"Error executing Python code: {error_msg}")
            return {
                "status": "error",
                "error": error_msg,
                "traceback": stack_trace,
                "language": "python",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            # Clean up sandbox
            if sandbox:
                try:
                    sandbox.close()
                except:
                    pass

    def execute_javascript(self,
                          code: str,
                          timeout: int = 30) -> Dict[str, Any]:
        """
        Execute JavaScript/Node.js code in E2B sandbox.

        Args:
            code: JavaScript code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with execution results
        """
        if not self.api_key or not CodeInterpreter:
            return {
                "status": "error",
                "error": "E2B not configured or not installed",
                "language": "javascript"
            }

        sandbox = None
        start_time = time.time()

        try:
            logger.info(f"Executing JavaScript code in E2B sandbox (timeout: {timeout}s)")

            sandbox = self._create_sandbox(timeout)
            if not sandbox:
                raise Exception("Failed to create sandbox")

            # Wrap JS code for execution in Python sandbox
            js_wrapper = f"""
import subprocess
import json

js_code = '''{code}'''

# Write JS code to file
with open('/tmp/script.js', 'w') as f:
    f.write(js_code)

# Execute with Node.js
result = subprocess.run(
    ['node', '/tmp/script.js'],
    capture_output=True,
    text=True,
    timeout={timeout}
)

print("STDOUT:", result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("RETURN_CODE:", result.returncode)
"""

            result = sandbox.notebook.exec_cell(js_wrapper)
            execution_time = time.time() - start_time

            # Parse output
            output_text = result.text if hasattr(result, 'text') else ""
            lines = output_text.split('\n')

            stdout = ""
            stderr = ""
            return_code = 0

            for line in lines:
                if line.startswith("STDOUT:"):
                    stdout = line[7:].strip()
                elif line.startswith("STDERR:"):
                    stderr = line[7:].strip()
                elif line.startswith("RETURN_CODE:"):
                    return_code = int(line[12:].strip())

            formatted_result = {
                "status": "success" if return_code == 0 else "error",
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "language": "javascript",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"JavaScript code executed in {execution_time:.2f}s")
            return formatted_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing JavaScript code: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "language": "javascript",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            if sandbox:
                try:
                    sandbox.close()
                except:
                    pass

    def execute_r(self,
                  code: str,
                  timeout: int = 30) -> Dict[str, Any]:
        """
        Execute R statistical code in E2B sandbox.

        Args:
            code: R code to execute
            timeout: Maximum execution time in seconds

        Returns:
            Dictionary with execution results
        """
        if not self.api_key or not CodeInterpreter:
            return {
                "status": "error",
                "error": "E2B not configured or not installed",
                "language": "r"
            }

        sandbox = None
        start_time = time.time()

        try:
            logger.info(f"Executing R code in E2B sandbox (timeout: {timeout}s)")

            sandbox = self._create_sandbox(timeout)
            if not sandbox:
                raise Exception("Failed to create sandbox")

            # Wrap R code for execution
            r_wrapper = f"""
import subprocess

r_code = '''{code}'''

# Write R code to file
with open('/tmp/script.R', 'w') as f:
    f.write(r_code)

# Execute with R
result = subprocess.run(
    ['Rscript', '/tmp/script.R'],
    capture_output=True,
    text=True,
    timeout={timeout}
)

print("STDOUT:", result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)
print("RETURN_CODE:", result.returncode)
"""

            result = sandbox.notebook.exec_cell(r_wrapper)
            execution_time = time.time() - start_time

            # Parse output
            output_text = result.text if hasattr(result, 'text') else ""
            lines = output_text.split('\n')

            stdout = ""
            stderr = ""
            return_code = 0

            for line in lines:
                if line.startswith("STDOUT:"):
                    stdout = line[7:].strip()
                elif line.startswith("STDERR:"):
                    stderr = line[7:].strip()
                elif line.startswith("RETURN_CODE:"):
                    return_code = int(line[12:].strip())

            formatted_result = {
                "status": "success" if return_code == 0 else "error",
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code,
                "language": "r",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

            logger.info(f"R code executed in {execution_time:.2f}s")
            return formatted_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing R code: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "language": "r",
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            if sandbox:
                try:
                    sandbox.close()
                except:
                    pass

    def execute_with_files(self,
                          code: str,
                          files: Dict[str, str],
                          language: str = "python",
                          timeout: int = 30) -> Dict[str, Any]:
        """
        Execute code with input files available.

        Args:
            code: Code to execute
            files: Dictionary mapping filename to content
            language: Programming language
            timeout: Maximum execution time

        Returns:
            Dictionary with execution results
        """
        if not self.api_key or not CodeInterpreter:
            return {
                "status": "error",
                "error": "E2B not configured or not installed",
                "language": language
            }

        sandbox = None
        start_time = time.time()

        try:
            logger.info(f"Executing {language} code with {len(files)} input files")

            sandbox = self._create_sandbox(timeout)
            if not sandbox:
                raise Exception("Failed to create sandbox")

            # Upload files to sandbox
            file_setup = "import os\n"
            for filename, content in files.items():
                # Escape content for Python string
                escaped_content = content.replace("'", "\\'").replace('\n', '\\n')
                file_setup += f"""
with open('{filename}', 'w') as f:
    f.write('''{escaped_content}''')
print(f"Created file: {filename}")
"""

            # Execute file setup
            sandbox.notebook.exec_cell(file_setup)

            # Execute the actual code based on language
            if language == "python":
                result = sandbox.notebook.exec_cell(code)
            else:
                # For other languages, use subprocess wrapper
                wrapper = self._create_subprocess_wrapper(code, language, timeout)
                result = sandbox.notebook.exec_cell(wrapper)

            execution_time = time.time() - start_time

            formatted_result = self._format_result(
                result,
                language,
                execution_time
            )

            formatted_result["input_files"] = list(files.keys())

            logger.info(f"Code with files executed successfully in {execution_time:.2f}s")
            return formatted_result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing code with files: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "language": language,
                "execution_time": execution_time,
                "timestamp": datetime.now().isoformat()
            }

        finally:
            if sandbox:
                try:
                    sandbox.close()
                except:
                    pass

    def _create_subprocess_wrapper(self, code: str, language: str, timeout: int) -> str:
        """Create subprocess wrapper for non-Python languages."""
        extensions = {
            "javascript": "js",
            "r": "R",
            "bash": "sh",
            "ruby": "rb"
        }

        commands = {
            "javascript": "node",
            "r": "Rscript",
            "bash": "bash",
            "ruby": "ruby"
        }

        ext = extensions.get(language, "txt")
        cmd = commands.get(language, "cat")

        return f"""
import subprocess

code = '''{code}'''

# Write code to file
with open('/tmp/script.{ext}', 'w') as f:
    f.write(code)

# Execute
result = subprocess.run(
    ['{cmd}', '/tmp/script.{ext}'],
    capture_output=True,
    text=True,
    timeout={timeout}
)

print(result.stdout)
if result.stderr:
    print("ERROR:", result.stderr)
"""

    def install_packages(self,
                        packages: List[str],
                        language: str = "python") -> Dict[str, Any]:
        """
        Install packages in the sandbox before code execution.

        Args:
            packages: List of package names to install
            language: Programming language (python, javascript, r)

        Returns:
            Installation status dictionary
        """
        if not self.api_key or not CodeInterpreter:
            return {
                "status": "error",
                "error": "E2B not configured",
                "language": language
            }

        install_commands = {
            "python": lambda pkgs: f"!pip install {' '.join(pkgs)}",
            "javascript": lambda pkgs: f"!npm install {' '.join(pkgs)}",
            "r": lambda pkgs: f"install.packages(c({','.join([f'\"{p}\"' for p in pkgs])}))"
        }

        if language not in install_commands:
            return {
                "status": "error",
                "error": f"Unsupported language for package installation: {language}",
                "language": language
            }

        install_code = install_commands[language](packages)

        # Use appropriate execution method
        if language == "python":
            result = self.execute_python(install_code, timeout=60)
        else:
            result = {
                "status": "error",
                "error": f"Package installation for {language} not yet implemented"
            }

        result["installed_packages"] = packages
        return result


# Module-level functions for direct tool registration
_tool_instance = E2BTool()

def run_python_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code in a safe sandbox."""
    return _tool_instance.execute_python(code, timeout)

def run_javascript_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute JavaScript code in a safe sandbox."""
    return _tool_instance.execute_javascript(code, timeout)

def run_r_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute R statistical code in a safe sandbox."""
    return _tool_instance.execute_r(code, timeout)

def run_code_with_files(code: str, files: Dict[str, str], language: str = "python") -> Dict[str, Any]:
    """Execute code with input files available."""
    return _tool_instance.execute_with_files(code, files, language)