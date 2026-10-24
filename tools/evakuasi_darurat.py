import os
import sqlite3
import shutil

# --- KONFIGURASI MUTLAK ---
# Sesuaikan 2 variabel ini jika path aktual di laptop Anda berbeda
LOCAL_BASE_DIR = "Raw"
CLOUD_BASE_DIR = "G:/My Drive/Raw"  # folder Google Drive yang tersinkron
DB_FILE = "history.sqlite"

def run_evacuation():
    if not os.path.exists(DB_FILE):
        print("[FATAL] history.sqlite tidak ditemukan! Pastikan skrip berada di folder yang benar.")
        return

    # 1. Akses Memori Inti
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_path FROM processed_files WHERE status = 'DONE'")
    
    # Simpan dalam Set untuk pencarian secepat kilat O(1)
    done_records = set(row[0] for row in c.fetchall())
    conn.close()

    print(f"[*] Memori dimuat: {len(done_records)} file berstatus DONE.")
    print("[*] Memulai Operasi Sapu Bersih ke GDrive...\n")

    moved_count = 0
    ignored_count = 0

    if not os.path.exists(LOCAL_BASE_DIR):
        print(f"[FATAL] Folder target lokal tidak ditemukan: {LOCAL_BASE_DIR}")
        return

    # 2. Pindai folder lokal
    for fg_name in os.listdir(LOCAL_BASE_DIR):
        fg_local_path = os.path.join(LOCAL_BASE_DIR, fg_name)
        
        if not os.path.isdir(fg_local_path):
            continue
            
        for filename in os.listdir(fg_local_path):
            if filename.startswith(('~', '.')) or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                continue
            
            local_file_path = os.path.join(fg_local_path, filename)
            agnostic_path = f"{fg_name}/{filename}" # Format: Fotografer/DSC_001.jpg
            
            # 3. Interogasi Database
            if agnostic_path in done_records:
                # File ini SUDAH dibuatkan watermark di masa lalu. EVAKUASI!
                cloud_fg_path = os.path.join(CLOUD_BASE_DIR, fg_name)
                os.makedirs(cloud_fg_path, exist_ok=True)
                
                cloud_file_path = os.path.join(cloud_fg_path, filename)
                
                try:
                    # CUT-PASTE MUTLAK
                    shutil.move(local_file_path, cloud_file_path)
                    print(f"[EVAKUASI] {agnostic_path} -> Terbang ke GDrive")
                    moved_count += 1
                except Exception as e:
                    print(f"[ERROR] Gagal menendang {agnostic_path}: {e}")
            else:
                # File belum pernah diproses (Mungkin baru terdownload sebagian/utuh). Biarkan!
                ignored_count += 1

    print("\n======================================")
    print(f"[*] OPERASI TRIAGE SELESAI")
    print(f"[-] File Dibuang ke Cloud (SSD Lega) : {moved_count} foto")
    print(f"[-] File Tertahan di Lokal (Belum Rilis): {ignored_count} foto")
    print("======================================")

if __name__ == "__main__":
    run_evacuation()