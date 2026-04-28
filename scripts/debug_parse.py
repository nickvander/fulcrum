import re
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ExtractedLineItem:
    sku: Optional[str] = None
    description: str = ""
    quantity: float = 0.0
    unit_cost: float = 0.0
    line_total: float = 0.0

def parse_amount(value):
    if not value: return 0.0
    try:
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        return float(cleaned) if cleaned else 0.0
    except: return 0.0

text = """Item
Quantity
Unit price
Amount
Hot Sale Silicone Coffee Machine Pads Separated 
Design Heat Resistant Multi-Sizes Silicone Kitchen 
Drain Baking Mats
120.00
USD 2.3000
USD 276.00
Hot Sale Silicone Coffee Machine Pads Separated 
Design Heat Resistant Multi-Sizes Silicone Kitchen 
Drain Baking Mats
70.00
USD 2.7000
USD 189.00
Smell Removal Sealing Rubber Cover Tub Stopper 
Anti-Smell Drain Silicone Floor Drain Anti-Odor Mat 
Floor Drain Cover for Kitchen
3,200.00
USD 0.4000
USD 1,280.00
"""

lines = [l.strip() for l in text.split('\n') if l.strip()]
items = []

i = 0
while i < len(lines):
    line = lines[i]
    # Look for a quantity-like line (numeric only)
    if re.match(r"^[0-9,]+\.?\d*$", line) and not any(c in line for c in "USDMXNEUR"):
        qty = parse_amount(line)
        
        # Look BACK for description
        desc_lines = []
        j = i - 1
        while j >= 0:
            prev_line = lines[j]
            # Stop if we hit a number or currency
            if parse_amount(prev_line) > 0 or any(c in prev_line for c in "USDMXNEUR"):
                break
            # Stop if we hit headers
            if prev_line.lower() in ["item", "description", "quantity", "amount", "unit price", "order details"]:
                break
            desc_lines.insert(0, prev_line)
            j -= 1
        
        if desc_lines:
            # Look FORWARD for prices
            price = 0.0
            total = 0.0
            k = i + 1
            if k < len(lines) and any(c in lines[k] for c in "USDMXNEUR"):
                price = parse_amount(lines[k])
                k += 1
            if k < len(lines) and any(c in lines[k] for c in "USDMXNEUR"):
                total = parse_amount(lines[k])
                k += 1
            
            items.append(ExtractedLineItem(
                description=" ".join(desc_lines),
                quantity=qty, unit_cost=price, line_total=total
            ))
            i = k
            continue
    i += 1

print(f"Total items found: {len(items)}")
for it in items:
    print(f"- {it.description[:50]}... (Qty: {it.quantity}, Price: {it.unit_cost}, Total: {it.line_total})")
