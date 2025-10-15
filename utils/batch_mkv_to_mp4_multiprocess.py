import os
import subprocess
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# 📂 Folderi
input_folder = r"V:\log_mkv"      # HDD
output_folder = r"V:\log"          # HDD
temp_folder = r"C:\temp_remux"     # SSD! 🚀

# ⚙️ Broj paralelnih procesa (na SSD-u može više!)
MAX_WORKERS = 8

start_time = time.time()

def remux_file(input_path):
    file_start = time.time()
    
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    final_output = os.path.join(output_folder, base_name + ".mp4")
    
    if os.path.exists(final_output):
        return f"⏩ Preskačem: {os.path.basename(final_output)}"
    
    # Temp putanje NA SSD-u
    temp_input = os.path.join(temp_folder, os.path.basename(input_path))
    temp_output = os.path.join(temp_folder, base_name + ".mp4")
    
    try:
        # 1️⃣ Kopiraj MKV sa HDD na SSD
        shutil.copy2(input_path, temp_input)
        
        # 2️⃣ Remux NA SSD-u (brzo!)
        command = [
            "ffmpeg",
            "-i", temp_input,
            "-vcodec", "copy",
            "-acodec", "copy",
            "-y",
            temp_output
        ]
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if result.returncode == 0 and os.path.exists(temp_output):
            # 3️⃣ Prebaci MP4 nazad na HDD
            shutil.move(temp_output, final_output)
            
            # 4️⃣ Obriši temp MKV sa SSD-a
            os.remove(temp_input)
            
            # 5️⃣ Obriši originalni MKV sa HDD-a
            #os.remove(input_path)
            
            file_time = time.time() - file_start
            total_time = time.time() - start_time
            return f"✅ OK: {base_name}.mp4 | {file_time:.2f}s (ukupno {total_time/60:.1f} min)"
        else:
            # Cleanup ako fail
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if os.path.exists(temp_output):
                os.remove(temp_output)
            
            file_time = time.time() - file_start
            return f"⚠️ Greška: {base_name} | {file_time:.2f}s"
            
    except Exception as e:
        # Cleanup
        if os.path.exists(temp_input):
            os.remove(temp_input)
        if os.path.exists(temp_output):
            os.remove(temp_output)
        
        file_time = time.time() - file_start
        return f"❌ Izuzetak: {base_name}: {e} | {file_time:.2f}s"

def main():
    os.makedirs(temp_folder, exist_ok=True)
    
    mkv_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.lower().endswith(".mkv")
    ]
    
    if not mkv_files:
        print("⚠️ Nema .mkv fajlova.")
        return
    
    print(f"🔍 Nađeno {len(mkv_files)} fajlova (~{len(mkv_files) * 1.3:.1f} GB)")
    print(f"🚀 NVMe: {temp_folder} (305 GB slobodno)")
    print(f"⚙️ Workers: {MAX_WORKERS}")
    print(f"💾 Temp zauzeće: ~{MAX_WORKERS * 1.3 * 2:.1f} GB\n")
    
    # ... ostatak koda
    
    # Napravi temp folder na SSD-u
    os.makedirs(temp_folder, exist_ok=True)
    
    mkv_files = [
        os.path.join(input_folder, f)
        for f in os.listdir(input_folder)
        if f.lower().endswith(".mkv")
    ]
    
    if not mkv_files:
        print("⚠️ Nema .mkv fajlova.")
        return
    
    print(f"🔍 Nađeno {len(mkv_files)} fajlova ({len(mkv_files) * 1.3:.1f} GB)")
    print(f"🚀 Koristim SSD temp: {temp_folder}\n")
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(remux_file, f): f for f in mkv_files}
        
        for future in as_completed(futures):
            print(future.result())
    
    # Obriši temp folder
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
    
    total_time = time.time() - start_time
    print(f"\n🏁 Ukupno vreme: {total_time/60:.2f} min")

if __name__ == "__main__":
    main()