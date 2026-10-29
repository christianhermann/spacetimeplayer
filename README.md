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

### 1. Launch with One Click (Windows)
Double-click:
- **`start.bat`** (or the **`Start PBS Space Time`** shortcut)

This starts the local Python server and automatically opens `http://localhost:8000` in your browser.

### 2. Or from the Command Line
```bash
# Install yt-dlp (one time)
pip install yt-dlp

# Run server
python app.py
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
