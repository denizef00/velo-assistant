# tests/test_velo.py

import unittest
from collections import deque
from core.llm_parser import LocalCommandParser
from modules.game_mode.ac_telemetry import ACTelemetryReader, SPageFilePhysics, SPageFileGraphic
from modules.game_mode.game_ctrl import GameController
from modules.dev_mode.dev_ctrl import DevController
from core.state_manager import StateManager, JarvisMode


class TestVeloUpgrade(unittest.TestCase):
    def test_llm_parser_memory(self):
        parser = LocalCommandParser()
        self.assertIsInstance(parser.history, deque)
        self.assertEqual(parser.history.maxlen, 6)

        # Test greeting addition
        parser.add_history("", "Good afternoon! Velo is ready.")
        self.assertEqual(len(parser.history), 1)
        self.assertIn("Good afternoon! Velo is ready.", parser.get_history_context())

        # Test sliding window maxlen=6
        for i in range(10):
            parser.add_history(f"User msg {i}", f"Velo reply {i}")
        self.assertEqual(len(parser.history), 6)
        # Oldest should be User msg 4
        self.assertIn("User msg 4", parser.get_history_context())
        self.assertNotIn("User msg 3", parser.get_history_context())

    def test_ac_telemetry(self):
        reader = ACTelemetryReader()
        self.assertFalse(reader.is_running())
        summary = reader.get_spoken_summary("fuel")
        self.assertIn("not running", summary.lower())

        # Test gear format helper
        self.assertEqual(reader._format_gear(0), "Reverse")
        self.assertEqual(reader._format_gear(1), "Neutral")
        self.assertEqual(reader._format_gear(2), "1st")
        self.assertEqual(reader._format_gear(3), "2nd")
        self.assertEqual(reader._format_gear(5), "4th")

    def test_game_mode(self):
        ctrl = GameController()
        # Media command should work
        res = ctrl.handle_command("volume up")
        self.assertEqual(res, "Volume increased.")
        # Telemetry should handle gracefully
        fuel_res = ctrl.handle_command("how much fuel do I have")
        self.assertIn("not running", fuel_res.lower())
        # HW telemetry should work
        hw_res = ctrl.get_hardware_telemetry()
        self.assertIn("CPU", hw_res)
        self.assertIn("RAM", hw_res)

    def test_dev_mode(self):
        ctrl = DevController()
        # Media command
        res = ctrl.handle_command("volume down")
        self.assertEqual(res, "Volume decreased.")
        # Clipboard check
        clip_res = ctrl.analyze_clipboard()
        self.assertTrue(isinstance(clip_res, str))

    def test_state_manager_routing(self):
        logs = []
        sm = StateManager(ui_callback=lambda m: logs.append(m))
        sm.tts.set_mute(True)  # silence for tests

        # Test greeting
        sm.greet_user()
        self.assertEqual(len(sm.llm_parser.history), 1)

        # Test mode switching
        sm.process_command("switch to game mode")
        self.assertEqual(sm.current_mode, JarvisMode.GAME)

        # In Game Mode, command routed to game_ctrl
        res = sm.process_command("check fuel")
        self.assertIn("not running", res.lower())

        # Switch to Dev Mode
        sm.process_command("switch to dev mode")
        self.assertEqual(sm.current_mode, JarvisMode.DEV)

        # In Dev Mode, command routed to dev_ctrl
        res = sm.process_command("volume up")
        self.assertEqual(res, "Volume increased.")

        # Switch to Desktop Mode
        sm.process_command("switch to desktop mode")
        self.assertEqual(sm.current_mode, JarvisMode.DESKTOP)


if __name__ == "__main__":
    unittest.main()
