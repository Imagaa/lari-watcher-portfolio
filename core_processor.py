import os
import time
import sqlite3
import json
from PIL import Image, ImageOps

# Load konfigurasi
with open('config.json', 'r') as f:
    CONFIG = json.load(f)

DB_FILE = CONFIG['database']['sqlite_file']

def init_db():
    """Inisialisasi tabel SQLite untuk State Management, Counters, dan Report."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS processed_files 
                 (file_path TEXT PRIMARY KEY, status TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS counters 
                 (folder_name TEXT PRIMARY KEY, last_number INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS report_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, folder_name TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                 final_name TEXT, size_kb REAL, status TEXT)''')
    conn.commit()
    conn.close()

def is_file_ready(filepath, delay=CONFIG['processing']['sync_delay_seconds']):
    """Anti-Partial Sync: Cek ukuran file 2 kali."""
    if not os.path.exists(filepath):
        return False
    try:
        size1 = os.path.getsize(filepath)
        time.sleep(delay)
        size2 = os.path.getsize(filepath)
        return size1 == size2 and size1 > 0
    except OSError:
        return False

def get_next_number(folder_name):
    """Mengambil dan mengunci nomor urut secara atomic."""
    conn = sqlite3.connect(DB_FILE, isolation_level='EXCLUSIVE')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO counters (folder_name, last_number) VALUES (?, 0)", (folder_name,))
    c.execute("UPDATE counters SET last_number = last_number + 1 WHERE folder_name = ?", (folder_name,))
    c.execute("SELECT last_number FROM counters WHERE folder_name = ?", (folder_name,))
    next_num = c.fetchone()[0]
    conn.commit()
    conn.close()
    return next_num

def log_to_report(folder_name, final_name, size_kb, status):
    """Mencatat hasil ke database untuk ditarik oleh Scheduler Excel."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO report_logs (folder_name, final_name, size_kb, status) VALUES (?, ?, ?, ?)", 
              (folder_name, final_name, size_kb, status))
    conn.commit()
    conn.close()

def process_image(filepath, folder_name):
    """Fungsi utama worker per file."""
    filename = os.path.basename(filepath)
    
    # 1. Cek SQLite
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT status FROM processed_files WHERE file_path=?", (filepath,))
    result = c.fetchone()
    
    if result:
        # Hanya skip jika statusnya sudah benar-benar selesai (DONE)
        if result[0] == 'DONE':
            conn.close()
            return f"[SKIP] {filename} sudah diproses."
        # Jika statusnya 'PENDING_LANDSCAPE', kode akan melewatinya dan lanjut memproses di bawah

    # 2. Validasi File Lock
    if not is_file_ready(filepath):
        conn.close()
        return f"[{folder_name} | WAIT] {filename} belum siap (partial sync)."

    size_kb = round(os.path.getsize(filepath) / 1024, 2)

    # Semua hasil masuk ke satu folder output
    output_dir = CONFIG['paths']['watermarked_folder']
    os.makedirs(output_dir, exist_ok=True)

    # 3. Proses Watermarking & Penentuan Orientasi Dinamis
    try:
        # Baca EXIF dan putar posisi secara fisik sebelum diproses
        img_raw = Image.open(filepath)
        img = ImageOps.exif_transpose(img_raw).convert("RGBA")
        
        # Pemilihan template berdasarkan orientasi fisik gambar
        if img.width >= img.height:
            logo_path = CONFIG['paths'].get('logo_landscape_path', 'logo-landscape.png')
            orientasi_str = "Landscape"
        else:
            logo_path = CONFIG['paths']['logo_path']
            orientasi_str = "Portrait"

        # Validasi ketersediaan file template twibbon
        if not os.path.exists(logo_path):
            if img.width >= img.height:
                c.execute("INSERT OR REPLACE INTO processed_files (file_path, status) VALUES (?, ?)", (filepath, 'PENDING_LANDSCAPE'))
                conn.commit()
                conn.close()
                return f"[{folder_name} | SKIP] {filename} tertunda (File template landscape tidak ditemukan di {logo_path})"
            else:
                conn.close()
                return f"[{folder_name} | ERROR] {filename} gagal: Template portrait tidak ditemukan."

        logo = Image.open(logo_path).convert("RGBA")

        # Tarik bingkai Twibbon agar ukurannya 100% sama persis dengan foto RAW
        logo_resized = logo.resize((img.width, img.height), Image.Resampling.LANCZOS)
        
        # Tempelkan bingkai dari sudut paling ujung (0, 0)
        img.paste(logo_resized, (0, 0), logo_resized)
        
        # Penomoran & Kode Huruf Dinamis
        seq_num = get_next_number(folder_name)
        prefix = CONFIG['processing']['prefix_name']
        
        # Ambil kode huruf dari dictionary photographers. Jika tidak terdaftar, gunakan "X"
        letter_code = CONFIG.get('photographers', {}).get(folder_name, {}).get('code', 'X')
        
        # Format: <prefix>_A0001.jpg
        new_filename = f"{prefix}_{letter_code}{seq_num:04d}.jpg"
        
        output_path = os.path.join(output_dir, new_filename)
        img.convert("RGB").save(output_path, "JPEG", quality=95)

        # 4. Catat di DB menggunakan REPLACE agar menimpa record PENDING_LANDSCAPE lama
        c.execute("INSERT OR REPLACE INTO processed_files (file_path, status) VALUES (?, ?)", (filepath, 'DONE'))
        conn.commit()
        conn.close()

        log_to_report(folder_name, new_filename, size_kb, 'BERHASIL')
        return f"[{folder_name} | SUCCESS] {filename} ({orientasi_str}) -> {new_filename}"
        
    except Exception as e:
        conn.close()
        log_to_report(folder_name, filename, size_kb, 'GAGAL')
        return f"[{folder_name} | ERROR] {filename} gagal: {str(e)}"