import os
import sys
from PIL import Image, ImageOps

def test_watermark(raw_path, twibbon_path, output_path):
    print(f"[*] Membaca Foto RAW: {raw_path}")
    print(f"[*] Membaca Twibbon : {twibbon_path}")
    
    try:
        # 1. Buka foto RAW dan pastikan orientasi EXIF tegak
        img_raw = Image.open(raw_path)
        img = ImageOps.exif_transpose(img_raw).convert("RGBA")
        
        # 2. Buka File Twibbon (WAJIB PNG TRANSPARAN)
        logo = Image.open(twibbon_path).convert("RGBA")

        # 3. Tarik bingkai Twibbon agar 100% sama dengan ukuran RAW (Full Frame)
        print("[*] Meresize Twibbon menyesuaikan dimensi RAW...")
        logo_resized = logo.resize((img.width, img.height), Image.Resampling.LANCZOS)
        
        # 4. Tempelkan Twibbon tepat di kordinat 0,0
        print("[*] Menempelkan Twibbon...")
        img.paste(logo_resized, (0, 0), logo_resized)

        # 5. Simpan Hasil
        img.convert("RGB").save(output_path, "JPEG", quality=95)
        print(f"\n[SUKSES] Hasil tester berhasil disimpan di:\n-> {output_path}")

    except Exception as e:
        print(f"\n[ERROR] Terjadi kesalahan: {e}")

# Pemakaian: python tools/test_twibbon.py <foto> <twibbon.png> [hasil.jpg]
# Pakai logo.png untuk foto portrait, logo-landscape.png untuk foto landscape.
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Pemakaian: python tools/test_twibbon.py <foto> <twibbon.png> [hasil.jpg]")
    elif not os.path.exists(sys.argv[2]):
        print(f"[FATAL] File Twibbon tidak ditemukan di {sys.argv[2]}")
    else:
        test_watermark(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "HASIL_TESTER_TWIBBON.jpg")
