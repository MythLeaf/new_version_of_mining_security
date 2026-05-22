import sys
import os
import ctypes

os.chdir(os.path.dirname(os.path.abspath(__file__)))

_overlapped_path = os.path.join(sys.exec_prefix, 'DLLs', '_overlapped.pyd')
if not os.path.exists(_overlapped_path):
    _overlapped_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_overlapped.pyd')
try:
    _overlapped_dll = ctypes.CDLL(_overlapped_path)
except OSError:
    _overlapped_dll = ctypes.CDLL('_overlapped.pyd')

class OVERLAPPED(ctypes.Structure):
    pass

_overlapped_dll.OVERLAPPED = OVERLAPPED

sys.modules["_overlapped"] = _overlapped_dll

print("Fake _overlapped installed, starting server with waitress...")

from waitress import serve
from api.main import app
serve(app, host='0.0.0.0', port=8000)
