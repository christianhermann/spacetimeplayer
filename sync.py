#!/usr/bin/env python3
"""Sync PBS Space Time videos, playlists, topic tags, related episodes, and AI summaries."""
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Load .env file if present (stdlib, no dotenv dependency needed)
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip().strip("'\""))

import yt_dlp

from app import DB_PATH, get_db, init_db

CHANNEL_VIDEOS_URL = "https://www.youtube.com/@pbsspacetime/videos"
CHANNEL_PLAYLISTS_URL = "https://www.youtube.com/@pbsspacetime/playlists"

TOPIC_TAXONOMY = {
    "Black Holes": [
        "black hole", "event horizon", "hawking", "singularity", "kerr", "quasar",
        "schwarzschild", "penrose", "spaghettification", "accretion", "supermassive",
        "information paradox", "firewall",
    ],
    "Quantum Mechanics": [
        "quantum", "wave function", "entanglement", "superposition", "schrodinger",
        "schrödinger", "heisenberg", "uncertainty", "bell", "double slit", "many worlds",
        "decoherence", "pilot wave", "bohm", "tunneling", "measurement", "copenhagen",
        "qubit", "teleportation", "casimir", "spin",
    ],
    "Relativity & Gravity": [
        "relativity", "spacetime", "space-time", "space time", "gravity", "gravitational",
        "lorentz", "time dilation", "speed of light", "wormhole", "alcubierre", "warp drive",
        "equivalence principle", "geodesic", "ligo", "frame dragging", "einstein",
        "faster than light", "ftl", "tachyon",
    ],
    "Cosmology & The Universe": [
        "universe", "cosmolog", "big bang", "inflation", "dark energy", "dark matter",
        "cosmic", "cmb", "hubble", "expansion", "multiverse", "heat death", "big rip",
        "big crunch", "fine tuning", "anthropic", "baryogenesis", "antimatter", "olbers",
        "horizon", "red shift", "redshift", "early universe",
    ],
    "Particle Physics & Standard Model": [
        "standard model", "quark", "lepton", "boson", "higgs", "neutrino", "fermion",
        "gluon", "photon", "electroweak", "qcd", "qed", "feynman", "lagrangian",
        "symmetry", "noether", "antiparticle", "muon", "cern", "lhc", "hadron",
        "proton", "electron", "neutron", "chirality", "gauge", "magnetic monopole",
    ],
    "Quantum Gravity & String Theory": [
        "string theory", "loop quantum", "holographic", "ads/cft", "planck",
        "quantum gravity", "emergent", "m-theory", "supersymmetry", "susy", "brane",
        "extra dimension", "graviton", "twistor", "amplituhedron", "toe", "theory of everything",
    ],
    "Stars & Astrophysics": [
        "neutron star", "pulsar", "magnetar", "supernova", "white dwarf", "stellar",
        "fusion", "galaxy", "galaxies", "milky way", "gamma ray", "fast radio burst",
        "cosmic ray", "strange star", "quark star", "kilonova", "nebula", "solar",
    ],
    "Exoplanets & Astrobiology": [
        "alien", "extraterrestrial", "fermi paradox", "seti", "exoplanet", "habitable",
        "biosignature", "life", "dyson", "kardashev", "drake equation", "great filter",
        "technosignature", "mars", "venus", "europa", "titan", "panspermia", "oort",
    ],
    "Time, Entropy & Information": [
        "entropy", "thermodynamic", "arrow of time", "time travel", "causality",
        "retrocausality", "information", "boltzmann", "maxwell", "chaos", "determinism",
        "free will", "simulation", "emergent", "complexity",
    ],
    "Space Time Journal Club & Q&A": [
        "journal club", "q&a", "challenge", "comments", "mailbag", "nobel", "prize",
    ],
}


def classify_topics(title: str, description: str, playlist_titles: list[str]) -> list[str]:
    text = f"{title} {description} {' '.join(playlist_titles)}".lower()
    matched = []
    for topic, keywords in TOPIC_TAXONOMY.items():
        if any(kw in text for kw in keywords):
            matched.append(topic)
    if not matched:
        matched.append("Cosmology & The Universe")
    return matched


def build_auto_summary(title: str, description: str, topics: list[str], playlists: list[str]) -> str:
    clean_desc = ""
    if description:
        lines = [
            ln.strip()
            for ln in description.splitlines()
            if ln.strip()
            and not ln.strip().startswith("http")
            and "patreon" not in ln.lower()
            and "merch" not in ln.lower()
            and "sponsor" not in ln.lower()
            and "sign up" not in ln.lower()
        ]
        if lines:
            clean_desc = " ".join(lines[:2])[:320]
    if clean_desc:
        return clean_desc
    pl_str = f" Part of the {', '.join(playlists[:2])} series." if playlists else ""
    return f"PBS Space Time episode exploring {', '.join(topics[:3])}: \"{title}\".{pl_str}"


def fetch_flat(url: str) -> list[dict]:
    ydl_opts = {"extract_flat": True, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return [e for e in (info.get("entries") or []) if e and e.get("id")]


def fetch_video_details(vid: str) -> dict:
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
            upload_date = info.get("upload_date") or ""
            if len(upload_date) == 8:
                upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:8]}"
            return {
                "id": vid,
                "description": info.get("description") or "",
                "published_at": upload_date,
            }
    except Exception:
        return {"id": vid, "description": "", "published_at": ""}


def generate_gemini_summaries(videos: list[dict], api_key: str) -> dict[str, str]:
    # ponytail: direct urllib call to Gemini REST API avoids 100MB google-genai SDK dependency
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    results = {}
    batch_size = 10
    import time
    for i in range(0, len(videos), batch_size):
        batch = videos[i : i + batch_size]
        items_text = "\n".join(
            f"- ID: {v['id']} | Title: {v['title']} | Topics: {', '.join(v['topics'])} | Playlists: {', '.join(v['playlists'])}"
            for v in batch
        )
        prompt = (
            "You are a physics educator summarizing PBS Space Time episodes by Matt O'Dowd.\n"
            "For each episode below, write a crisp 2-sentence overview explaining the core physics question, "
            "key concepts covered, and how it connects to broader physics topics.\n"
            "Return ONLY a valid JSON object mapping video ID to its summary string.\n\n"
            f"{items_text}"
        )
        req_body = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            }
        ).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})
        
        # Retry with exponential backoff on 503 / timeout
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=45) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    parsed = json.loads(text)
                    if isinstance(parsed, dict):
                        results.update(parsed)
                        print(f"    Summarized batch {i // batch_size + 1} ({len(results)}/{len(videos)} episodes)...")
                    break
            except Exception as exc:
                if attempt == 2:
                    print(f"Gemini batch warning: {exc}", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
    return results


def sync_catalog(full_details: bool = False, summarize: bool = False) -> None:
    init_db(DB_PATH)
    print("1/4 Fetching @pbsspacetime video catalog...")
    raw_videos = fetch_flat(CHANNEL_VIDEOS_URL)
    print(f"    Found {len(raw_videos)} videos on channel.")

    print("2/4 Fetching @pbsspacetime playlists...")
    raw_playlists = fetch_flat(CHANNEL_PLAYLISTS_URL)

    def _fetch_pl(pl_entry):
        pl_id = pl_entry.get("id")
        pl_url = pl_entry.get("url") or f"https://www.youtube.com/playlist?list={pl_id}"
        try:
            entries = fetch_flat(pl_url)
            return {
                "id": pl_id,
                "title": pl_entry.get("title") or "Untitled Playlist",
                "description": pl_entry.get("description") or "",
                "entries": entries,
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        playlists_data = [p for p in pool.map(_fetch_pl, raw_playlists) if p and p["entries"]]
    print(f"    Synced {len(playlists_data)} playlists.")

    video_playlists: dict[str, list[str]] = {}
    playlist_neighbors: dict[str, list[str]] = {}
    for pl in playlists_data:
        vids_in_pl = [e["id"] for e in pl["entries"] if e.get("id")]
        for idx, vid in enumerate(vids_in_pl):
            video_playlists.setdefault(vid, []).append(pl["title"])
            neighbors = playlist_neighbors.setdefault(vid, [])
            if idx > 0:
                neighbors.append(vids_in_pl[idx - 1])
            if idx + 1 < len(vids_in_pl):
                neighbors.append(vids_in_pl[idx + 1])

    with get_db(DB_PATH) as conn:
        existing = {
            r["id"]: dict(r)
            for r in conn.execute("SELECT id, description, published_at, summary FROM videos")
        }

    # Fetch rich descriptions/dates for the latest videos (or all if --full)
    detail_limit = len(raw_videos) if full_details else 20
    to_enrich = [
        v["id"]
        for v in raw_videos[:detail_limit]
        if not existing.get(v["id"], {}).get("description")
    ]
    enriched_map = {}
    if to_enrich:
        print(f"3/4 Enriching metadata for {len(to_enrich)} recent episodes...")
        with ThreadPoolExecutor(max_workers=6) as pool:
            for item in pool.map(fetch_video_details, to_enrich):
                enriched_map[item["id"]] = item
    else:
        print("3/4 Episode metadata up to date.")

    # Build catalog records and topic index
    catalog = []
    topic_buckets: dict[str, list[str]] = {}
    for idx, entry in enumerate(raw_videos):
        vid = entry["id"]
        title = entry.get("title") or "Untitled Episode"
        prev = existing.get(vid, {})
        enr = enriched_map.get(vid, {})
        description = enr.get("description") or prev.get("description") or entry.get("description") or ""
        published_at = enr.get("published_at") or prev.get("published_at") or ""
        duration = int(entry.get("duration") or 0)
        view_count = int(entry.get("view_count") or 0)
        thumbs = entry.get("thumbnails") or []
        thumbnail = thumbs[-1]["url"] if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
        pls = video_playlists.get(vid, [])
        topics = classify_topics(title, description, pls)
        for t in topics:
            topic_buckets.setdefault(t, []).append(vid)

        summary = prev.get("summary") or build_auto_summary(title, description, topics, pls)
        catalog.append(
            {
                "id": vid,
                "title": title,
                "description": description,
                "published_at": published_at,
                "upload_index": idx,
                "duration": duration,
                "view_count": view_count,
                "thumbnail": thumbnail,
                "summary": summary,
                "topics": topics,
                "playlists": pls,
            }
        )

    # Optional Gemini batch summarization
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if summarize and api_key:
        print("    Generating AI episode summaries via Gemini API...")
        ai_summaries = generate_gemini_summaries(catalog[:75], api_key)
        for item in catalog:
            if item["id"] in ai_summaries:
                item["summary"] = ai_summaries[item["id"]]

    # Compute related episodes (shared playlist neighbors first, then shared topics)
    for item in catalog:
        vid = item["id"]
        rel = []
        for nb in playlist_neighbors.get(vid, []):
            if nb != vid and nb not in rel:
                rel.append(nb)
        if len(rel) < 5:
            for t in item["topics"]:
                for candidate in topic_buckets.get(t, []):
                    if candidate != vid and candidate not in rel:
                        rel.append(candidate)
                        if len(rel) >= 6:
                            break
                if len(rel) >= 6:
                    break
        item["related_ids"] = rel[:6]

    print("4/4 Saving to SQLite database...")
    with get_db(DB_PATH) as conn:
        for item in catalog:
            conn.execute(
                """
                INSERT INTO videos (
                    id, title, description, published_at, upload_index,
                    duration, view_count, thumbnail, summary, auto_topics, related_ids
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    description = CASE WHEN excluded.description != '' THEN excluded.description ELSE videos.description END,
                    published_at = CASE WHEN excluded.published_at != '' THEN excluded.published_at ELSE videos.published_at END,
                    upload_index = excluded.upload_index,
                    duration = excluded.duration,
                    view_count = excluded.view_count,
                    thumbnail = excluded.thumbnail,
                    summary = excluded.summary,
                    auto_topics = excluded.auto_topics,
                    related_ids = excluded.related_ids
                """,
                (
                    item["id"],
                    item["title"],
                    item["description"],
                    item["published_at"],
                    item["upload_index"],
                    item["duration"],
                    item["view_count"],
                    item["thumbnail"],
                    item["summary"],
                    json.dumps(item["topics"]),
                    json.dumps(item["related_ids"]),
                ),
            )

        conn.execute("DELETE FROM playlist_videos")
        conn.execute("DELETE FROM playlists")
        Known_vids = {c["id"] for c in catalog}
        for pl in playlists_data:
            valid_entries = [e for e in pl["entries"] if e.get("id")]
            conn.execute(
                "INSERT INTO playlists (id, title, description, video_count) VALUES (?, ?, ?, ?)",
                (pl["id"], pl["title"], pl["description"], len(valid_entries)),
            )
            for pos, entry in enumerate(valid_entries):
                evid = entry["id"]
                if evid not in Known_vids:
                    # Also ensure playlist-only older videos exist in videos table
                    thumbs = entry.get("thumbnails") or []
                    thumb = thumbs[-1]["url"] if thumbs else f"https://i.ytimg.com/vi/{evid}/hqdefault.jpg"
                    t_title = entry.get("title") or "PBS Space Time Episode"
                    if t_title in ("[Private video]", "[Deleted video]"):
                        continue
                    t_topics = classify_topics(t_title, "", [pl["title"]])
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO videos (
                            id, title, upload_index, duration, thumbnail, summary, auto_topics, related_ids
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            evid,
                            t_title,
                            9999 + pos,
                            int(entry.get("duration") or 0),
                            thumb,
                            build_auto_summary(t_title, "", t_topics, [pl["title"]]),
                            json.dumps(t_topics),
                            json.dumps([]),
                        ),
                    )
                    Known_vids.add(evid)
                conn.execute(
                    "INSERT OR IGNORE INTO playlist_videos (playlist_id, video_id, position) VALUES (?, ?, ?)",
                    (pl["id"], evid, pos),
                )

    print(f"Synced {len(Known_vids)} total videos and {len(playlists_data)} playlists into {DB_PATH.name}.")


if __name__ == "__main__":
    full_flag = "--full" in sys.argv
    sum_flag = "--summarize" in sys.argv
    sync_catalog(full_details=full_flag, summarize=sum_flag)
