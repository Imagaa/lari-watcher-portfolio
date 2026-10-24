import sqlite3
import os

DB_FILE = 'history.sqlite'

def migrate_memory():
    if not os.path.exists(DB_FILE):
        print("[!] File history.sqlite tidak ditemukan.")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Ambil semua data memori lama
    c.execute("SELECT file_path FROM processed_files")
    rows = c.fetchall()
    
    print(f"[*] Menemukan {len(rows)} rekam jejak. Memulai operasi bedah path...")
    
    migrated_count = 0
    for row in rows:
        old_path = row[0]
        
        # Standarisasi slash untuk Windows & Mac
        normalized_path = old_path.replace('\\', '/')
        parts = normalized_path.split('/')
        
        # Ekstrak HANYA NamaFolder/NamaFile.jpg
        if len(parts) >= 2:
            new_path = f"{parts[-2]}/{parts[-1]}"
            
            # Jika path lama dan baru berbeda, lakukan Update
            if new_path != old_path:
                try:
                    c.execute("UPDATE processed_files SET file_path = ? WHERE file_path = ?", (new_path, old_path))
                    migrated_count += 1
                except sqlite3.IntegrityError:
                    # Jika tidak sengaja terduplikasi di DB, hapus path lama agar bersih
                    c.execute("DELETE FROM processed_files WHERE file_path = ?", (old_path,))

    conn.commit()
    conn.close()
    
    print(f"[*] SUCCESS: {migrated_count} memori berhasil diterjemahkan ke format Agnostik (Folder/File).")
    print("[*] Operasi selesai. Anda bisa menghapus file migrate_db.py ini jika mau.")

if __name__ == '__main__':
    migrate_memory()