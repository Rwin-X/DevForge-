"""Worker QObjects for anything slow enough to freeze the UI if run on
the main thread: RSA keypair generation, and file encryption/decryption
above a size threshold. Communicates back to the UI exclusively through
signals - never call a widget method directly from these.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from core.ciphers import CipherError, _rsa_generate_keypair


class RsaKeygenWorker(QObject):
    """Generates an RSA keypair off the main thread. Key generation at
    2048+ bits routinely takes long enough to visibly stall a UI."""

    finished = pyqtSignal(str, str)   # public_pem, private_pem
    failed = pyqtSignal(str)

    def __init__(self, bits: int):
        super().__init__()
        self._bits = bits

    def run(self) -> None:
        try:
            public_pem, private_pem = _rsa_generate_keypair(self._bits)
            self.finished.emit(public_pem, private_pem)
        except Exception as exc:  # noqa: BLE001 - surface any failure to the UI
            self.failed.emit(str(exc))


class FileCryptoWorker(QObject):
    """Runs a byte-safe cipher's file_encrypt_fn/file_decrypt_fn off the
    main thread. Large files (video, disk images) can take long enough
    through AES/RSA-hybrid wrapping that this must not block the UI."""

    finished = pyqtSignal(bytes)
    failed = pyqtSignal(str)

    def __init__(self, fn, data: bytes, key1: str, key2: str):
        super().__init__()
        self._fn = fn
        self._data = data
        self._key1 = key1
        self._key2 = key2

    def run(self) -> None:
        try:
            result = self._fn(self._data, self._key1, self._key2)
            self.finished.emit(result)
        except CipherError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(f"Unexpected error: {exc}")
