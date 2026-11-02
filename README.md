# PBS Space Time Companion 🌌

A lean, local companion app to explore, watch, and keep track of [PBS Space Time](https://www.youtube.com/@pbsspacetime) videos and series.

I love PBS Space Time, but YouTube can get quite messy when you're trying to follow multi-part playlists, track foundational physics topics, or remember which episodes you've already seen. This companion solves that with less clutter.

> **Vibecoded with care.** Feel free to fork, modify, or do whatever you want with it!

---

## ✨ Features

- **📺 Docked Split-View Player**: Watch episodes directly inside the app with YouTube's IFrame API.
- **⏱️ Auto-Progress Tracking**: Saves your exact playback seconds every 5s; auto-marks episodes as *Watched* when you reach 90%.
- **⛶ Fullscreen Ready**: Native YouTube fullscreen button + dedicated browser fullscreen toggle.
- **📚 Curated Playlists & Topics**: Explore series in sequence (*Standard Model*, *Black Holes*, *Quantum Gravity*, *Cosmology*, etc.) with visual progress bars.
- **⭐ Chosen / Queue**: Bookmark episodes to your personal watchlist.
- **📝 Personal Notes & Custom Tags**: Write takeaways, timestamps, and equations per episode—saved automatically.
- **🤖 Optional AI Summaries**: Enrich episodes with physics summaries and prerequisite links via Google Gemini. (Free API tier is sufficent)
- **♥ Support Link**: Direct link to the [PBS Space Time Patreon](https://www.patreon.com/pbsspacetime) to support Matt O'Dowd and the team.

---

## 🚀 Quick Start

### 1. Launch on Linux / Ubuntu
In the terminal, run:
```bash
./start.sh
```
- Sets the terminal window title to `pbs_spacetime_player_terminal`.
- Starts the local companion server and opens `http://localhost:8000` in your default browser (`xdg-open`).
- Closing the terminal window automatically and cleanly stops the server (handles `SIGHUP`/`SIGTERM` without lingering port locks).

#### Ubuntu Desktop & App Menu Integration
To integrate the companion into your GNOME / Ubuntu application dash, dock, and desktop:
```bash
./install-desktop-launcher.sh
```
- Automatically generates the transparent logo icon (`static/pbsspacetime-logo.png`).
- Adds **PBS Space Time Companion** to your Ubuntu application menu (`~/.local/share/applications`).
- Places an executable shortcut on your Desktop (`~/Desktop` or `~/Schreibtisch`).

To cleanly remove the desktop entries at any time:
```bash
./uninstall-desktop-launcher.sh
```

### 2. Launch on Windows
Double-click:
- **`start.bat`** (or the **`Start PBS Space Time`** shortcut)

### 3. Or Manually from Command Line
```bash
# Install dependencies (one time)
pip install yt-dlp   # on Ubuntu/Debian: pip3 install yt-dlp

# Run server
python app.py        # on Linux: python3 app.py
```

---

## 🔄 Syncing Channel Episodes

To refresh the catalog with the latest PBS Space Time uploads and playlists:
- Click **↻ Sync Channel** in the top navigation bar, OR
- Run in terminal:
  ```bash
  python sync.py
  ```

### (Optional) AI Summaries with Gemini
1. Copy `.env.example` to `.env`.
2. Add your free Gemini API key:
   ```env
   GEMINI_API_KEY=your_key_here
   ```
3. Run:
   ```bash
   python sync.py --summarize
   ```

---

## 🛠️ Tech Stack

- **Backend**: Python standard library (`http.server`, `sqlite3`, `urllib.request`). No heavy frameworks.
- **Frontend**: Vanilla HTML5, modern dark-mode CSS, and vanilla JS with the official YouTube IFrame Player API.
- **Database**: Local SQLite database (`spacetime.db`).

---

## 📄 License

[MIT License](LICENSE) — free for everyone to use, modify, and build upon.
