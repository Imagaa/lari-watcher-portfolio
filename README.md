# Lari Watcher

An automatic photo pipeline for running events. Several photographers upload to their own Google Drive folders. The watcher picks up each new photo, applies the event frame (twibbon), renames it with a sequential code, and writes everything to one output folder and an Excel log.

## How it works

- **One watcher per photographer.** `watchdog` monitors each folder listed in `config.json`. On startup, photos that are already in those folders are queued too (backlog sweep).
- **Thread pool.** Photos are processed in parallel, up to `max_workers` at a time.
- **Partial-sync guard.** The file size is checked twice a few seconds apart, so files that are still downloading from Drive are skipped.
- **Orientation-aware frames.** EXIF rotation is applied first. Portrait photos get `logo.png`, landscape photos get `logo-landscape.png`, and the frame is stretched to the full photo size.
- **Sequential naming.** Each photographer has a letter code, and a SQLite counter produces names like `Event Run_A0001.jpg`, without collisions between threads.
- **Restart-safe.** Processed files are stored in SQLite, so restarting the watcher never processes the same photo twice.
- **Excel report.** A background thread exports the log to `Master_Log.xlsx` every 60 seconds, with one sheet per photographer.

## Usage

```bash
python -m venv venv
venv\Scripts\activate        # Windows; use `source venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
python main.py
```

Set photographer folders, the output folder, the file name prefix, and the worker count in `config.json`. Replace `logo.png` and `logo-landscape.png` with your own transparent PNG frames.

## Tools

Run these from the project root:

| Script | Purpose |
|---|---|
| `tools/test_twibbon.py <photo> <frame.png>` | Preview a frame on one photo before the event |
| `tools/evakuasi_darurat.py` | Free local disk space: move already-processed photos to the Drive folder |
| `tools/audit_lokal.py` | Reconcile local folders: move processed photos to a trash folder and unprocessed ones to Drive |
| `tools/migrate_db.py` | Convert stored paths in the database to the `Folder/File` format |
