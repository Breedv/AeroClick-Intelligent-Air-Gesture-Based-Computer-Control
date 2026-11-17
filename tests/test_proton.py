from src.Proton import Proton


def test_commands_and_sleep():
    p=Proton()
    assert p.respond("Proton launch gesture recognition")[1]=="start"
    assert p.respond("Proton stop gesture recognition")[1]=="stop"
    assert p.respond("copy")[1]=="copy"
    assert p.respond("paste")[1]=="paste"
    assert p.respond("date")[0]
    assert p.respond("time")[0]
    p.respond("bye")
    assert p.respond("start")[1] is None
    p.respond("wake up")
    assert p.respond("start")[1]=="start"


def test_file_navigation_bounds(tmp_path):
    p=Proton()
    p.path=tmp_path
    (tmp_path/"folder").mkdir()
    (tmp_path/"sample.txt").write_text("test")
    assert "folder" in p.respond("list files")[0]
    assert "file number" in p.respond("open 0")[0]
    assert "file number" in p.respond("open 99")[0]
    p.respond("open 1")
    assert p.path==tmp_path/"folder"
    p.respond("back")
    assert p.path==tmp_path


def test_search_and_location_escape_text(monkeypatch):
    opened=[]
    monkeypatch.setattr("src.Proton.webbrowser.open",opened.append)
    p=Proton()
    p.respond("search gesture control & python")
    assert "gesture%20control%20%26%20python" in opened[-1]
    p.respond("find location")
    p.respond("New Delhi")
    assert opened[-1].endswith("New%20Delhi")
