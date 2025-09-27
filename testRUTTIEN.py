#!/usr/bin/env python3
from decimal import Decimal, ROUND_HALF_UP
import sys

def make_instr(value, places=2) -> str:
    """
    Trả về chuỗi dạng *#$****x****#$* với x là số có 'places' chữ số thập phân.
    """
    d = Decimal(str(value)).quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
    return f"*#$****{d}****#$*"

if __name__ == "__main__":
    # Nếu truyền tham số: python script.py 0.01 0.2 30.5
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            print(make_instr(arg))
    else:
        # Mẫu test mặc định
        samples = [1.20]
        for v in samples:
            print("sjaskjasckjsanckjnsackjsan"+make_instr(v)+"jnjajajka")
