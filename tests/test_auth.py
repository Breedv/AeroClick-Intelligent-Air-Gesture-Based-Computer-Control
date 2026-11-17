import sqlite3
import pytest
from src.auth import AuthStore, ITERATIONS


def test_register_verify_reload_salts_and_no_plaintext(tmp_path):
    path=tmp_path/"accounts.db"
    store=AuthStore(path)
    assert not store.has_users()
    store.register("Alice","very secure pass")
    store.register("Bob","very secure pass")
    assert store.has_users()
    assert AuthStore(path).verify("alice","very secure pass")
    assert not store.verify("Alice","incorrect pass")
    assert not store.verify("missing","very secure pass")
    assert not store.verify("' OR 1=1 --","very secure pass")
    with sqlite3.connect(path) as db:
        rows=db.execute("SELECT salt,digest,iterations FROM users").fetchall()
    assert rows[0][0] != rows[1][0] and rows[0][1] != rows[1][1]
    assert rows[0][2] == ITERATIONS
    assert b"very secure pass" not in path.read_bytes()


@pytest.mark.parametrize("name,password",[("a","long-password"),("bad name","long-password"),("valid","short"),("valid","x"*129)])
def test_invalid_registration(tmp_path,name,password):
    with pytest.raises(ValueError):
        AuthStore(tmp_path/"a.db").register(name,password)


def test_duplicate_case_insensitive(tmp_path):
    store=AuthStore(tmp_path/"a.db")
    store.register("Alice","valid-password")
    with pytest.raises(ValueError,match="already exists"):
        store.register("ALICE","another-password")
