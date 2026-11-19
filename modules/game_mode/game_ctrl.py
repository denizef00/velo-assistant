# modules/game_mode/game_ctrl.py

import os
import subprocess
from typing import Optional
import psutil

try:
    from modules.desktop_mode.system_ctrl import SystemController
    from modules.game_mode.ac_telemetry import ACTelemetryReader
except ImportError:
    from moduls.desktop_mode.system_ctrl import SystemController
    from modules.game_mode.ac_telemetry import ACTelemetryReader


class GameController(SystemController):
    """Game Mode controller with Assetto Corsa telemetry, racing launcher, and live hardware monitoring."""

    def __init__(self, llm_parser=None):
        super().__init__()
        self.telemetry = ACTelemetryReader()
        self.llm_parser = llm_parser

    def launch_racing_profile(self) -> str:
        """Launches Content Manager (or Assetto Corsa) and Discord together."""
        # 1. Launch Game / Launcher (Content Manager preferred for AC)
        game_res = self.app_launcher.launch("Content Manager")
        if "couldn't find" in game_res.lower():
            game_res = self.app_launcher.launch("Assetto Corsa")

        # 2. Launch Discord
        discord_res = self.app_launcher.launch("Discord")

        return "Launching racing setup with Discord. Have a good session!"

    def get_hardware_telemetry(self) -> str:
        """Returns CPU, RAM, and optional thermal sensor readings."""
        cpu = psutil.cpu_percent(interval=0.2)
        ram = psutil.virtual_memory().percent
        temp = self._get_wmi_temperature()

        if temp is not None:
            return f"CPU is at {cpu} percent, RAM is at {ram} percent, and hardware temperature is {temp:.0f} degrees."
        return f"CPU usage is at {cpu} percent, and RAM usage is at {ram} percent."

    def get_thermal_status(self) -> str:
        """Queries hardware thermal sensors via Windows WMI."""
        temp = self._get_wmi_temperature()
        if temp is not None:
            return f"Hardware temperature is currently around {temp:.1f} degrees Celsius."

        cpu = psutil.cpu_percent(interval=0.2)
        return f"Hardware thermal sensors are not reporting on this motherboard. CPU load is at {cpu} percent."

    @staticmethod
    def _get_wmi_temperature() -> Optional[float]:
        """Queries Windows ACPI Thermal Zone via WMI using PowerShell fallback."""
        try:
            cmd = [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature -ErrorAction SilentlyContinue | Select-Object -ExpandProperty CurrentTemperature"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=1.5)
            output = res.stdout.strip()
            if output:
                kelvin_deci = int(output.split()[0])
                celsius = (kelvin_deci - 2732) / 10.0
                if 10.0 <= celsius <= 120.0:
                    return celsius
        except Exception:
            pass
        return None

    def handle_command(self, command: str) -> Optional[str]:
        cmd = command.lower().strip()

        # 0. Sabit Ses & Medya Kontrolleri (En yüksek öncelik - In-game media keys)
        media_response = self.media_ctrl.handle_command(cmd)
        if media_response:
            return media_response

        # 1. Game Profile Launcher
        if any(k in cmd for k in [
            "start racing", "launch racing", "launch assetto corsa setup",
            "assetto corsa setup", "racing setup", "start assetto",
            "play assetto", "setup racing", "launch assetto"
        ]):
            return self.launch_racing_profile()

        # 2. Assetto Corsa Canlı Telemetri Komutları
        if any(k in cmd for k in ["fuel", "how much fuel", "gas level"]):
            return self.telemetry.get_spoken_summary("fuel")

        elif any(k in cmd for k in ["tire", "tyre", "tire temp", "tyre temp", "tires", "tyres"]):
            return self.telemetry.get_spoken_summary("tires")

        elif any(k in cmd for k in ["lap time", "current lap", "lap"]):
            return self.telemetry.get_spoken_summary("lap")

        elif any(k in cmd for k in ["telemetry", "car status", "how is the car", "racing telemetry"]):
            return self.telemetry.get_spoken_summary("general")

        elif any(k in cmd for k in ["how fast", "speed check", "current speed"]):
            return self.telemetry.get_spoken_summary("speed")

        # 3. Donanım Sıcaklığı ve Sistem Durumu (psutil + WMI)
        elif any(k in cmd for k in [
            "hardware temp", "hardware temperature", "cpu temp",
            "pc temp", "thermal", "gpu temp", "temperature"
        ]):
            return self.get_thermal_status()

        elif any(k in cmd for k in [
            "system status", "cpu usage", "ram usage", "cpu/ram",
            "hardware status", "pc performance", "hardware usage"
        ]):
            return self.get_hardware_telemetry()

        # 4. Genel Masaüstü / Sistem Komutlarına Düşme (App launching, searches, etc.)
        return super().handle_command(command)

    def execute_llm_intent(self, parsed_data: dict) -> Optional[str]:
        intent = parsed_data.get("intent", "UNKNOWN")
        if intent == "SYSTEM_STATUS":
            return self.get_hardware_telemetry()

        return super().execute_llm_intent(parsed_data)
