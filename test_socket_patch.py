import ctypes
import sys
import os

_ov_path = os.path.join(sys.exec_prefix, 'DLLs', '_overlapped.pyd')
if not os.path.exists(_ov_path):
    _ov_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_overlapped.pyd')
try:
    _ov = ctypes.CDLL(_ov_path)
except OSError:
    _ov = ctypes.CDLL('_overlapped.pyd')
class OVERLAPPED(ctypes.Structure):
    pass
_ov.OVERLAPPED = OVERLAPPED
sys.modules["_overlapped"] = _ov

import socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("socket.socket() OK!")
    s.close()
except Exception as e:
    print(f"socket.socket() FAILED: {e}")

import _socket
print(f"_socket module: {_socket}")
print(f"_socket.socket: {_socket.socket}")

try:
    raw = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    print(f"raw _socket.socket() OK: {raw}")
    raw.close()
except Exception as e:
    print(f"raw _socket.socket() FAILED: {e}")
