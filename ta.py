import subprocess

def shrink_overlay(input_path, output_path, shrink_percent=18):
    # Tính tỷ lệ còn lại sau khi thu nhỏ
    scale_factor = (100 - shrink_percent) / 100.0
    
    # FFmpeg filter: scale + overlay
    filter_str = f"[0:v]scale=iw*{scale_factor}:ih*{scale_factor}[small];" \
                 f"[0:v][small]overlay=(W-w)/2:(H-h)/2"
    
    command = [
        "ffmpeg", "-i", input_path, "-filter_complex", filter_str,
        "-c:a", "copy",  # giữ nguyên audio
        output_path
    ]
    subprocess.run(command)

# Ví dụ sử dụng: thu nhỏ 18%
shrink_overlay("virtual.mp4", "virtual_shrinked.mp4", shrink_percent=18)
