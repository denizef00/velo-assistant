# modules/game_mode/ac_telemetry.py

import ctypes
import mmap
from typing import Optional, Dict, Any, Tuple


class SPageFilePhysics(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
        ("fuel", ctypes.c_float),
        ("gear", ctypes.c_int),
        ("rpm", ctypes.c_int),
        ("steerAngle", ctypes.c_float),
        ("speedKmh", ctypes.c_float),
        ("velocity", ctypes.c_float * 3),
        ("accG", ctypes.c_float * 3),
        ("wheelSlip", ctypes.c_float * 4),
        ("wheelLoad", ctypes.c_float * 4),
        ("wheelsPressure", ctypes.c_float * 4),
        ("wheelAngularSpeed", ctypes.c_float * 4),
        ("tyreWear", ctypes.c_float * 4),
        ("tyreDirtyLevel", ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),
        ("camberRAD", ctypes.c_float * 4),
        ("suspensionTravel", ctypes.c_float * 4),
    ]


class SPageFileGraphic(ctypes.Structure):
    _fields_ = [
        ("packetId", ctypes.c_int),
        ("status", ctypes.c_int),
        ("session", ctypes.c_int),
        ("currentTime", ctypes.c_wchar * 15),
        ("lastTime", ctypes.c_wchar * 15),
        ("bestTime", ctypes.c_wchar * 15),
        ("split", ctypes.c_wchar * 15),
        ("completedLaps", ctypes.c_int),
        ("position", ctypes.c_int),
        ("iCurrentTime", ctypes.c_int),
    ]


class ACTelemetryReader:
    """Reads Assetto Corsa Windows Shared Memory and provides spoken telemetry summaries."""

    FILE_MAP_READ = 0x0004
    PHYSICS_TAGS = ["Local\\acpmf_physics", "acpmf_physics"]
    GRAPHICS_TAGS = ["Local\\acpmf_graphics", "acpmf_graphics"]

    def __init__(self):
        self._kernel32 = getattr(ctypes.windll, "kernel32", None)

    def _mapping_exists(self, tag_name: str) -> bool:
        """Checks if the named shared memory file mapping exists in Windows."""
        if not self._kernel32:
            return False
        try:
            handle = self._kernel32.OpenFileMappingW(self.FILE_MAP_READ, False, tag_name)
            if handle:
                self._kernel32.CloseHandle(handle)
                return True
        except Exception:
            pass
        return False

    def is_running(self) -> bool:
        """Determines if Assetto Corsa is actively running with valid shared memory."""
        for tag in self.PHYSICS_TAGS:
            if self._mapping_exists(tag):
                physics = self._read_physics(tag)
                if physics and physics.packetId > 0:
                    return True
        return False

    def _read_physics(self, tag_name: str) -> Optional[SPageFilePhysics]:
        try:
            with mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics), tagname=tag_name, access=mmap.ACCESS_READ) as mm:
                return SPageFilePhysics.from_buffer_copy(mm)
        except Exception:
            return None

    def _read_graphics(self, tag_name: str) -> Optional[SPageFileGraphic]:
        try:
            with mmap.mmap(-1, ctypes.sizeof(SPageFileGraphic), tagname=tag_name, access=mmap.ACCESS_READ) as mm:
                return SPageFileGraphic.from_buffer_copy(mm)
        except Exception:
            return None

    def get_telemetry(self) -> Optional[Dict[str, Any]]:
        """Extracts key telemetry metrics: fuel, tire temps, gear, speed, and lap time."""
        physics_data = None
        for tag in self.PHYSICS_TAGS:
            if self._mapping_exists(tag):
                physics_data = self._read_physics(tag)
                if physics_data and physics_data.packetId > 0:
                    break

        if not physics_data or physics_data.packetId == 0:
            return None

        graphics_data = None
        for tag in self.GRAPHICS_TAGS:
            if self._mapping_exists(tag):
                graphics_data = self._read_graphics(tag)
                if graphics_data and graphics_data.packetId > 0:
                    break

        fl = float(physics_data.tyreCoreTemperature[0])
        fr = float(physics_data.tyreCoreTemperature[1])
        rl = float(physics_data.tyreCoreTemperature[2])
        rr = float(physics_data.tyreCoreTemperature[3])

        gear_code = int(physics_data.gear)
        gear_str = self._format_gear(gear_code)

        lap_time = "0:00.000"
        if graphics_data:
            lap_time = self._format_lap_time(graphics_data.currentTime, graphics_data.iCurrentTime)

        return {
            "fuel": round(float(physics_data.fuel), 1),
            "tire_temps": {
                "fl": round(fl, 1),
                "fr": round(fr, 1),
                "rl": round(rl, 1),
                "rr": round(rr, 1),
                "front_avg": round((fl + fr) / 2.0, 1),
                "rear_avg": round((rl + rr) / 2.0, 1)
            },
            "gear": gear_code,
            "gear_str": gear_str,
            "speed_kmh": round(float(physics_data.speedKmh), 1),
            "lap_time": lap_time
        }

    @staticmethod
    def _format_gear(gear_code: int) -> str:
        """Converts Assetto Corsa gear integers (0=R, 1=N, 2=1st, etc.) to spoken strings."""
        if gear_code == 0:
            return "Reverse"
        elif gear_code == 1:
            return "Neutral"
        else:
            actual = gear_code - 1
            suffix = "th"
            if actual == 1:
                suffix = "st"
            elif actual == 2:
                suffix = "nd"
            elif actual == 3:
                suffix = "rd"
            return f"{actual}{suffix}"

    @staticmethod
    def _format_lap_time(raw_str: str, millis: int) -> str:
        """Returns clean formatted lap time string."""
        clean_raw = str(raw_str).strip("\x00 \t\r\n")
        if clean_raw and any(char.isdigit() for char in clean_raw):
            return clean_raw
        if millis > 0:
            mins = millis // 60000
            secs = (millis % 60000) / 1000.0
            return f"{mins}:{secs:05.2f}"
        return "0:00.000"

    def get_spoken_summary(self, topic: str = "general") -> str:
        """Generates natural 1-2 sentence spoken feedback for Velo TTS."""
        telemetry = self.get_telemetry()
        if not telemetry:
            return "Assetto Corsa is not running right now."

        fuel = telemetry["fuel"]
        tires = telemetry["tire_temps"]
        gear_str = telemetry["gear_str"]
        speed = telemetry["speed_kmh"]
        lap_time = telemetry["lap_time"]

        topic_clean = topic.lower().strip()

        if "fuel" in topic_clean:
            return f"Fuel is at {fuel:.1f} liters."

        if any(w in topic_clean for w in ["tire", "tyre", "temp"]):
            return (
                f"Front tires are at {tires['fl']:.0f} and {tires['fr']:.0f} degrees, "
                f"and rear tires are around {tires['rear_avg']:.0f} degrees."
            )

        if any(w in topic_clean for w in ["lap", "time"]):
            return f"Current lap time is {lap_time}."

        if "speed" in topic_clean or "gear" in topic_clean:
            return f"Speed is {speed:.0f} kilometers per hour in {gear_str} gear."

        # Default comprehensive summary
        return (
            f"Fuel is at {fuel:.1f} liters, and front tires are around {tires['front_avg']:.0f} degrees. "
            f"Currently doing {speed:.0f} kilometers per hour in {gear_str} gear."
        )
