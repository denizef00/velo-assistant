# moduls/__init__.py - backwards compatibility alias for modules
import sys
import modules

sys.modules["moduls"] = modules
