import ctypes
import sys
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

_overlapped_path = os.path.join(sys.exec_prefix, 'DLLs', '_overlapped.pyd')
if not os.path.exists(_overlapped_path):
    _overlapped_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_overlapped.pyd')
try:
    _overlapped = ctypes.CDLL(_overlapped_path)
except OSError:
    _overlapped = ctypes.CDLL('_overlapped.pyd')

class OVERLAPPED(ctypes.Structure):
    pass

_overlapped.OVERLAPPED = OVERLAPPED

sys.modules["_overlapped"] = _overlapped

print("Fake _overlapped module installed")
