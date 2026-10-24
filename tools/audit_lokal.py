import os
import sqlite3
import shutil

# Konfigurasi Path
LOCAL_BASE_DIRS = [
    "Raw",
    "D:/Raw"
]
CLOUD_BASE_DIR = "G:/My Drive/Raw"  # folder Google Drive yang tersinkron
TRASH_DIR = "Aman_Dihapus"
DB_FILE = "history.sqlite"

def run_audit():
    if not os.path.exists(DB_FILE):
        print("[FATAL] Database tidak ditemukan!")
        return

    # 1. Ekstrak Universal Set dari Database
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT file_path FROM processed_files WHERE status = 'DONE'")
    
    done_records = set()
    for row in c.fetchall():
        # Kebal terhadap perbedaan path (C:/... atau G:/...)
        path = row[0].replace('\\', '/')
        parts = path.split('/')
        if len(parts) >= 2:
            agnostic_path = f"{parts[-2]}/{parts[-1]}" # Format: Fotografer/DSC_001.jpg
            done_records.add(agnostic_path)
    conn.close()

    print(f"[*] Buku Besar Dimuat: {len(done_records)} foto telah ber-watermark.")
    print("[*] Memulai Pengecekan Folder Lokal\n")

    safe_count = 0
    rescue_count = 0

    # 2. Pindai semua folder lokal
    for base_dir in LOCAL_BASE_DIRS:
        print(f"\n[*] Menyapukan Radar pada: {base_dir}")
        if not os.path.exists(base_dir):
            print(f"[SKIP] Folder tidak ditemukan/sudah bersih.")
            continue

        for fg_name in os.listdir(base_dir):
            fg_local_path = os.path.join(base_dir, fg_name)
            
            if not os.path.isdir(fg_local_path):
                continue
                
            for filename in os.listdir(fg_local_path):
                if filename.startswith(('~', '.')) or not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    continue
                
                local_file_path = os.path.join(fg_local_path, filename)
                agnostic_path = f"{fg_name}/{filename}"
                
                # 3. KEPUTUSAN HAKIM
                if agnostic_path in done_records:
                    target_dir = os.path.join(TRASH_DIR, fg_name)
                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, filename)
                    
                    shutil.move(local_file_path, target_path)
                    print(f"[AMAN] {agnostic_path} -> Pindah ke Tong Sampah")
                    safe_count += 1
                else:
                    target_dir = os.path.join(CLOUD_BASE_DIR, fg_name)
                    os.makedirs(target_dir, exist_ok=True)
                    target_path = os.path.join(target_dir, filename)
                    
                    shutil.move(local_file_path, target_path)
                    print(f"[RESCUE] {agnostic_path} -> Lempar ke GDrive")
                    rescue_count += 1

    print("\n======================================")
    print(f"[*] REKONSILIASI SELESAI")
    print(f"[-] Foto Aman Dihapus (Pindah ke {TRASH_DIR}) : {safe_count} foto")
    print(f"[-] Foto Diselamatkan (Terlempar ke {CLOUD_BASE_DIR}) : {rescue_count} foto")
    print("======================================")

if __name__ == "__main__":
    run_audit()