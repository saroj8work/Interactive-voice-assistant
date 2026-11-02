"""
Timer and Reminder Management Tool.
Handles relative time delays, countdowns, and active timers.
"""
import time
import threading
from typing import Dict, Any, List
from app.tools.base import BaseTool, ToolResult


class TimerTool(BaseTool):
    name = "timer_manager"
    description = "Sets countdown timers, reminders, and tracks remaining time."
    parameters_schema = {
        "duration": {"type": "integer", "description": "Duration number"},
        "unit": {
            "type": "string",
            "description": "Unit: 'seconds', 'minutes', 'hours'",
        },
        "label": {"type": "string", "description": "Optional label/reminder text"},
    }

    _active_timers: List[Dict[str, Any]] = []

    def execute(
        self,
        duration: int = 10,
        unit: str = "seconds",
        label: str = "Timer",
        reminder_text: str = "",
        **kwargs,
    ) -> ToolResult:
        u = unit.lower()
        multiplier = 1
        if "min" in u:
            multiplier = 60
        elif "hour" in u or "hr" in u:
            multiplier = 3600

        total_seconds = int(duration) * multiplier
        final_label = reminder_text or label or "Timer"

        timer_id = f"timer_{int(time.time())}_{len(self._active_timers)}"
        timer_info = {
            "id": timer_id,
            "label": final_label,
            "duration_seconds": total_seconds,
            "unit": unit,
            "duration_val": duration,
            "start_time": time.time(),
            "target_time": time.time() + total_seconds,
            "completed": False,
        }

        self._active_timers.append(timer_info)

        # Background thread to mark timer completed
        def _countdown(target_sec, t_info):
            time.sleep(target_sec)
            t_info["completed"] = True

        threading.Thread(
            target=_countdown, args=(total_seconds, timer_info), daemon=True
        ).start()

        msg = f"Timer set for {duration} {unit} for '{final_label}'."
        return ToolResult(
            success=True,
            data=timer_info,
            message=msg,
        )

    @classmethod
    def get_active_timers(cls) -> List[Dict[str, Any]]:
        now = time.time()
        for t in cls._active_timers:
            rem = max(0, int(t["target_time"] - now))
            t["remaining_seconds"] = rem
        return cls._active_timers
