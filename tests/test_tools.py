"""
Unit tests for Tool Execution.
"""
import tempfile
from pathlib import Path
from app.tools.calculator import CalculatorTool
from app.tools.system import SystemTool
from app.tools.weather import WeatherTool
from app.tools.notes import NoteTool
from app.tools.timer import TimerTool


def test_calculator_tool():
    calc = CalculatorTool()
    res = calc.execute(expression="25 * 4 + 10")
    assert res.success is True
    assert res.data["result"] == 110


def test_calculator_safety():
    calc = CalculatorTool()
    # Attempts to run arbitrary code should be blocked safely by AST validator
    res = calc.execute(expression="__import__('os').system('ls')")
    assert res.success is False


def test_system_tool_datetime():
    tool = SystemTool()
    res = tool.execute(action="datetime")
    assert res.success is True
    assert "time" in res.data
    assert "date" in res.data


def test_system_tool_stats():
    tool = SystemTool()
    res = tool.execute(action="stats")
    assert res.success is True
    assert "cpu_cores" in res.data


def test_weather_tool():
    tool = WeatherTool()
    res = tool.execute(location="Tokyo")
    assert res.success is True
    assert "Tokyo" in res.message


def test_notes_tool():
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = NoteTool(notes_dir=Path(tmpdir))
        res = tool.execute(action="create", title="Test Note", content="Hello test note")
        assert res.success is True
        assert res.data["title"] == "Test Note"

        list_res = tool.execute(action="list")
        assert list_res.success is True
        assert len(list_res.data) == 1


def test_timer_tool():
    tool = TimerTool()
    res = tool.execute(duration=5, unit="seconds", label="Quick Test")
    assert res.success is True
    assert res.data["duration_seconds"] == 5
