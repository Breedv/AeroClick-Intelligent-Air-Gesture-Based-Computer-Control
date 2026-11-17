"""Local authentication. No default account, plaintext password, or network call."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path


ITERATIONS = 600_000


def data_dir():
    if os.getenv("GESTURE_CONTROL_DATA_DIR"):
        path = Path(os.environ["GESTURE_CONTROL_DATA_DIR"]).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path
    root = Path(os.getenv("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    path = root / "GestureControlRecognition"
    path.mkdir(parents=True, exist_ok=True)
    return path


class AuthStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else data_dir() / "accounts.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY COLLATE NOCASE, "
                       "salt BLOB NOT NULL, digest BLOB NOT NULL, iterations INTEGER NOT NULL)")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        try:
            with db:
                yield db
        finally:
            db.close()

    def has_users(self):
        with self._connect() as db:
            return db.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None

    def register(self, username, password):
        username = username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
            raise ValueError("Username: use 3–32 letters, numbers, dots, underscores or hyphens.")
        if not 10 <= len(password) <= 128:
            raise ValueError("Use a password between 10 and 128 characters.")
        salt = secrets.token_bytes(32)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
        try:
            with self._connect() as db:
                db.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (username, salt, digest, ITERATIONS))
        except sqlite3.IntegrityError:
            raise ValueError("That username already exists.") from None
        return username

    def verify(self, username, password):
        if len(password) > 128 or len(username) > 32:
            return False
        with self._connect() as db:
            row = db.execute("SELECT salt, digest, iterations FROM users WHERE username = ?",
                             (username.strip(),)).fetchone()
        salt, expected, iterations = row or (b"\x00"*32, b"\x00"*32, ITERATIONS)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected) and row is not None
