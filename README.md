# GhostPad

A tiny subtle LLM window. Uses an API (OpenAI-compatible).

---

## Features

* Small white text box, no border
* Always on top
* Click center to type
* Default Ctrl+Enter to send
* Right-click for settings
* Hidden from taskbar / Alt+Tab
* Drag edges to move/resize (long-press near the edge, then drag)

---

## Install

1. Install Python 3.7+
2. Download or clone this repo, then open a terminal in the repo directory
3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

---

## Use

1. Start:

   ```bash
   python ghostpad.py
   ```
2. Right-click → **LLM Settings** → set your API key, base URL, and model
3. Click center → type → **Ctrl+Enter** to send

---

## Right-Click Menu

* **LLM Settings** — Configure your LLM provider: API key, base URL (OpenAI-style), model name, and basic params (e.g., temperature, max tokens). Works with OpenAI or any service that follows the same API format.

* **Set Hotkey** — Set global shortcuts (e.g., show/hide window). Enter a key combo and save.

* **Start New Chat** — Clear the current conversation and start a blank one. *Note: history for this session will be cleared.*

* **History** — View the transcript for the current session.

* **Help** — Opens this document.

* **Hide** — Hides the text window. Use the configured show/hide hotkey to bring it back.

* **Exit** — Exit. *History will be cleared*

---

## Troubleshoot

**No response**

* Check your internet connection
* Check that your API key, base URL, and model are set correctly

**Window won’t move**

* Make sure you are long-pressing near the window border (not the center)
* Hold for \~0.5s, then drag

**Configuration edits are not saved**

* Click **Save** after modifying settings (you may need to manually enlarge the settings window to see the button)

---

## Privacy

* All settings from the LLM Settings tab are stored locally at:
  `C:\Users\<YourUsername>\.ghostpad\config.ini`
* No telemetry is collected by GhostPad; requests are sent only to your configured LLM provider.
