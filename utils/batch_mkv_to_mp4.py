import os
import subprocess
import time

# Putanja do foldera sa .mkv fajlovima
input_folder = r"V:\log_mkv"
output_folder = r"V:\log"

# Prolazak kroz sve fajlove u folderu
start_script = time.time()
total = 0

for filename in os.listdir(input_folder):
    start_file = time.time()
    
    if filename.lower().endswith(".mkv"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, os.path.splitext(filename)[0] + ".mp4")
        
        if os.path.exists(output_path):
            print(f"⏩ Preskačem (već postoji): {os.path.basename(output_path)}")
            continue

        # ffmpeg komanda (bez recompressovanja)
        command = [
            "ffmpeg",
            "-i", input_path,
            "-vcodec", "copy",
            "-acodec", "copy",
            output_path
        ]

        print(f"Konvertujem: {filename} -> {os.path.basename(output_path)} -> time: ")
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        total += 1
        print(f"\t DONE: {os.path.basename(output_path)} --> {time.time()-start_file:,.2f} s")

print(f"✅ Završeno! Svi MKV fajlovi ({total}) su prebačeni u MP4. {(time.time()-start_script)/60:,.2f} min")
