"""
System Information and Control Tool.
Safely provides date/time, OS metrics, resource usage, and launchable desktop utilities.
"""
import datetime
import os
import platform
import subprocess
from app.tools.base import BaseTool, ToolResult


class SystemTool(BaseTool):
    name = "system"
    description = "Provides system time, date, platform info, resource stats, and opens standard utility apps."
    parameters_schema = {
        "action": {
            "type": "string",
            "description": "Action type: 'datetime', 'stats', or 'launch_app'",
        },
        "app_name": {
            "type": "string",
            "description": "App to launch (notepad, calculator, terminal)",
        },
    }

    ALLOWED_APPS = {
        "notepad": "notepad.exe" if platform.system() == "Windows" else "nano",
        "calculator": "calc.exe" if platform.system() == "Windows" else "bc",
        "terminal": "cmd.exe" if platform.system() == "Windows" else "bash",
    }

    def execute(self, action: str = "datetime", app_name: str = "", **kwargs) -> ToolResult:
        act = action.lower()

        if act == "datetime" or act == "time" or act == "date":
            now = datetime.datetime.now()
            time_str = now.strftime("%I:%M %p")
            date_str = now.strftime("%A, %B %d, %Y")
            msg = f"It is currently {time_str} on {date_str}."
            return ToolResult(
                success=True,
                data={"time": time_str, "date": date_str, "iso": now.isoformat()},
                message=msg,
            )

        elif act == "stats" or act == "system_stats":
            os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"
            py_ver = platform.python_version()
            cpu_count = os.cpu_count() or 1
            msg = f"System running {os_info} with {cpu_count} CPU cores. Python runtime version is {py_ver}."
            return ToolResult(
                success=True,
                data={
                    "os": os_info,
                    "cpu_cores": cpu_count,
                    "python_version": py_ver,
                },
                message=msg,
            )

        elif act == "launch_app" or (app_name and app_name.lower() in self.ALLOWED_APPS):
            target = (app_name or act).lower()
            if target in self.ALLOWED_APPS:
                bin_cmd = self.ALLOWED_APPS[target]
                try:
                    subprocess.Popen(bin_cmd, shell=True)
                    return ToolResult(
                        success=True,
                        data={"app": target, "command": bin_cmd},
                        message=f"Successfully launched {target}.",
                    )
                except Exception as e:
                    return ToolResult(
                        success=False,
                        error=str(e),
                        message=f"Failed to launch {target}: {str(e)}",
                    )
            else:
                return ToolResult(
                    success=False,
                    error="App not allowed",
                    message=f"For safety, '{target}' cannot be launched. Allowed apps: {list(self.ALLOWED_APPS.keys())}",
                )

        # Default fallback
        now = datetime.datetime.now()
        return ToolResult(
            success=True,
            data={"time": now.strftime("%I:%M %p")},
            message=f"Current time is {now.strftime('%I:%M %p')}.",
        )
