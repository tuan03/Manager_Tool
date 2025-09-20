# Tạo file và ghi dữ liệu
with open("output.txt", "w", encoding="utf-8") as f:
    # 20 dòng, dấu cách từ 6 đến 25 (20 giá trị)
    for spaces in range(6, 26):  
        line = " " * spaces + "matrinh3@gmail.com"
        f.write(line + "\n")
