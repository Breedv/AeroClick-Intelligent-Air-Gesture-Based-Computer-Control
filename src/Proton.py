"""Original Proton commands, routed through the authenticated dashboard."""
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import os
import re
import webbrowser


class Proton:
    def __init__(self):
        self.awake = True
        self.path = Path.home()
        self.files = []
        self.awaiting_location = False

    def _list(self):
        self.files = sorted(self.path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        return str(self.path) + "\n" + "\n".join(f"{i+1}. {p.name}" for i, p in enumerate(self.files))

    def respond(self, text):
        text = re.sub(r"^proton\s*", "", text.strip(), flags=re.I)
        command = text.lower()
        if "wake up" in command:
            self.awake = True
            return "I am ready.", None
        if not self.awake:
            return "Proton is asleep. Say 'wake up' to resume.", None
        if self.awaiting_location:
            self.awaiting_location = False
            webbrowser.open("https://www.google.com/maps/search/"+quote(text))
            return f"Opened Maps for {text}.", None
        if command in ("bye", "sleep"):
            self.awake = False
            return "Proton is asleep.", None
        if "launch gesture" in command or command == "start":
            return "Starting gesture control.", "start"
        if "stop gesture" in command or command == "stop":
            return "Stopping gesture control.", "stop"
        if command in ("exit", "terminate"):
            return "Closing safely.", "exit"
        if "date" in command:
            return datetime.now().strftime("%B %d, %Y"), None
        if "time" in command:
            return datetime.now().strftime("%H:%M:%S"), None
        if command.startswith("search "):
            webbrowser.open("https://www.google.com/search?q="+quote(text[7:]))
            return "Opened your search in the default browser.", None
        if "location" in command:
            place = re.sub(r".*?location\s*", "", text, flags=re.I)
            if not place:
                self.awaiting_location = True
                return "Which place should I find?", None
            webbrowser.open("https://www.google.com/maps/search/"+quote(place))
            return f"Opened Maps for {place}.", None
        if command in ("copy", "paste", "page", "pest"):
            return "Switch to the target application; the shortcut runs in two seconds.", "copy" if command == "copy" else "paste"
        try:
            if command in ("list", "list files"):
                return self._list(), None
            if command in ("back", "go back"):
                self.path = self.path.parent
                return self._list(), None
            if command.startswith("open "):
                index = int(command.split()[-1])-1
                if not 0 <= index < len(self.files):
                    return "Use a file number from 'list files'.", None
                selected = self.files[index]
                if selected.is_dir():
                    self.path = selected
                    return self._list(), None
                os.startfile(selected)
                return f"Opened {selected.name}.", None
        except (OSError, ValueError) as exc:
            return f"Cannot complete file command: {exc}", None
        if "name" in command or "hello" in command:
            return "I am Proton, your gesture-control assistant.", None
        return "Commands: start, stop, date, time, search …, location …, list files, open N, back, copy, paste, sleep, wake up, exit.", None


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.app import main
    main()
