import re

def parse_amount(value):
    if not value:
        return 0.0
    try:
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

text = """Hot Sale Silicone Coffee Machine Pads Separated 
Design Heat Resistant Multi-Sizes Silicone Kitchen 
Drain Baking Mats
120.00
USD 2.3000
USD 276.00"""

lines = [line.strip() for line in text.split('\n') if line.strip()]
print(f"Lines: {lines}")

i = 3 # 120.00
line = lines[i]
is_qty = bool(re.match(r"^[0-9,]+\.?\d*$", line) and not any(c in line for c in "USDMXNEUR"))
print(f"Line: {line}, Is Qty: {is_qty}")

j = i - 1
desc_lines = []
while j >= 0:
    prev_line = lines[j]
    amt = parse_amount(prev_line)
    is_header = prev_line.lower() in ["item", "amount"]
    print(f"  Prev: {prev_line}, Amt: {amt}, Header: {is_header}")
    if amt > 0 or is_header:
        break
    desc_lines.insert(0, prev_line)
    j -= 1

print(f"Desc lines: {desc_lines}")
