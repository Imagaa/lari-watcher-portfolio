import time
import os
import json
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import core_processor

with open('config.json', 'r') as f:
    CONFIG = json.load(f)

class WatcherHandler(FileSystemEventHandler):
    def __init__(self, executor, fg_name):
        self.executor = executor
        self.fg_name = fg_name  # Nama fotografer langsung diikat ke handler ini

    def on_created(self, event):
        if not event.is_directory:
            filepath = event.src_path
            filename = os.path.basename(filepath)
            
            if not filename.startswith(('~', '.')):
                self.executor.submit(worker_task, filepath, self.fg_name)

    # Keluarkan fungsi worker agar bisa diakses oleh Watcher maupun Backlog Sweeper
def worker_task(filepath, fg_name):
    result = core_processor.process_image(filepath, fg_name)
    print(result)

def excel_reporter_daemon():
    db_file = CONFIG['database']['sqlite_file']
    excel_path = CONFIG['paths']['excel_report']
    
    while True:
        time.sleep(60) 
        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            df = pd.read_sql_query("SELECT * FROM report_logs", conn)
            conn.close()
            
            if df.empty:
                continue

            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                grouped = df.groupby('folder_name')
                for folder, group in grouped:
                    sheet_data = group[['timestamp', 'final_name', 'size_kb', 'status']].copy()
                    sheet_data.insert(0, 'No', range(1, 1 + len(sheet_data)))
                    sheet_data.rename(columns={
                        'timestamp': 'Timestamp',
                        'final_name': 'Nama File',
                        'size_kb': 'Ukuran File (KB)',
                        'status': 'Status'
                    }, inplace=True)
                    
                    safe_sheet_name = str(folder)[:31]
                    sheet_data.to_excel(writer, index=False, sheet_name=safe_sheet_name)
            
            print(f"[REPORTER] Master Log Excel diperbarui: {time.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"[REPORTER ERROR] Gagal menulis Excel: {str(e)}")

if __name__ == "__main__":
    watermarked_folder = CONFIG['paths']['watermarked_folder']
    os.makedirs(watermarked_folder, exist_ok=True)
    
    core_processor.init_db()

    reporter_thread = threading.Thread(target=excel_reporter_daemon, daemon=True)
    reporter_thread.start()

    executor = ThreadPoolExecutor(max_workers=CONFIG['processing']['max_workers'])
    observer = Observer()
    
    print("[*] Menginisialisasi Sensor Watcher...")
    
    # Looping untuk memasang sensor di setiap path fotografer
    active_watchers = 0
    for fg_name, fg_data in CONFIG['photographers'].items():
        fg_path = fg_data['path']
        if os.path.exists(fg_path):
            event_handler = WatcherHandler(executor, fg_name)
            # recursive=False karena kita sudah memantau path paling spesifik
            observer.schedule(event_handler, fg_path, recursive=False)
            print(f"  [OK] Memantau {fg_name}: {fg_path}")
            active_watchers += 1
        else:
            print(f"  [SKIP] Folder tidak ditemukan (Disconnected?): {fg_path}")

    print(f"\n[*] Sistem Aktif. Total target dipantau: {active_watchers}")
    print(f"[*] Folder Output Tunggal: {watermarked_folder}")
    print(f"[*] Limit Global Worker: {CONFIG['processing']['max_workers']} proses bersamaan")
    print(f"[*] Excel Reporter Aktif (Update tiap 60 detik)")
    
    # --- SISTEM PENYAPU BACKLOG (Mengeksekusi file yang sudah ada) ---
    print("\n[*] Memindai file yang sudah ada di folder (Backlog)...")
    backlog_count = 0
    for fg_name, fg_data in CONFIG['photographers'].items():
        fg_path = fg_data['path']
        if os.path.exists(fg_path):
            for filename in os.listdir(fg_path):
                if not filename.startswith(('~', '.')) and filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    filepath = os.path.join(fg_path, filename)
                    executor.submit(worker_task, filepath, fg_name)
                    backlog_count += 1
    print(f"[*] Ditemukan {backlog_count} foto. Mesin mulai mengeksekusi antrean...\n")
    print("[*] Tekan Ctrl+C untuk mematikan mesin.\n")
    # -----------------------------------------------------------------

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[!] Menerima sinyal berhenti. Menunggu worker selesai...")
        executor.shutdown(wait=True)
    observer.join()