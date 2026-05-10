#!/usr/bin/env python3
"""
import_po.py — Import a Purchase Order from a supplier document.

Supports: PDF, JPG, PNG, AVIF, HTML, TXT files.
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' is required. Install with: pip install requests")
    sys.exit(1)

DEFAULT_API_URL = "http://localhost:8000/api/v1"

# File extension to MIME type mapping
MIME_MAP = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".avif": "image/avif",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
}

def print_summary(data):
    """Premium-feel summary of the extraction results."""
    print("\n" + "="*85)
    print(f"{'📦 PURCHASE ORDER EXTRACTION SUMMARY':^85}")
    print("="*85)
    
    # Metadata
    print(f"  {'Supplier:':<20} {data.get('vendor_name', 'Unknown')}")
    print(f"  {'PO Number:':<20} {data.get('po_number', 'None')}")
    print(f"  {'Invoice #:':<20} {data.get('invoice_number', 'None')}")
    print(f"  {'Currency:':<20} {data.get('currency', 'USD')}")
    print(f"  {'Confidence:':<20} {data.get('confidence', 0.0) * 100:.1f}%")
    print("-" * 85)
    
    # Items Table
    items = data.get("items", [])
    if not items:
        print("  [!] No items extracted.")
    else:
        # Header
        print(f"  {'Description':<45} | {'Qty':>8} | {'Price':>10} | {'Total':>10}")
        print(f"  {'-' * 45}-+-{'-' * 8}-+-{'-' * 10}-+-{'-' * 10}")
        
        for item in items:
            desc = item.get("description", "No description")
            qty = item.get("quantity", 0)
            cost = item.get("unit_cost", 0)
            total = item.get("line_total", 0)
            
            # Simple word wrap for description
            words = desc.split()
            lines = []
            curr_line = []
            for word in words:
                if len(" ".join(curr_line + [word])) <= 43:
                    curr_line.append(word)
                else:
                    lines.append(" ".join(curr_line))
                    curr_line = [word]
            if curr_line:
                lines.append(" ".join(curr_line))
            
            # Print first line with data
            if lines:
                print(f"  {lines[0]:<45} | {qty:>8.2f} | {cost:>10.2f} | {total:>10.2f}")
                # Print remaining description lines
                for extra_line in lines[1:]:
                    print(f"  {extra_line:<45} | {'':>8} | {'':>10} | {'':>10}")
            print(f"  {'-' * 45}-+-{'-' * 8}-+-{'-' * 10}-+-{'-' * 10}")

    # Footer
    subtotal = data.get("subtotal", 0)
    shipping = data.get("shipping_cost", 0)
    tax = data.get("tax_amount", 0)
    total_amount = data.get("total_amount", 0)
    
    if shipping > 0 or tax > 0:
        print(f"  {'Subtotal:':<68} {subtotal:>10.2f}")
        if shipping > 0:
            print(f"  {'Shipping:':<68} {shipping:>10.2f}")
        if tax > 0:
            print(f"  {'Tax:':<68} {tax:>10.2f}")
        print("-" * 85)
        
    print(f"  {'TOTAL EXTRACTED AMOUNT:':<68} {total_amount:>10.2f}")
    print("="*85 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Import Purchase Order from PDF/Image")
    parser.add_argument("file_path", help="Path to the document file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"Base API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--auto-create", action="store_true", help="Automatically create the PO if parsing is successful")
    parser.add_argument("--supplier-id", type=int, help="Supplier ID for auto-creation")
    args = parser.parse_args()

    file_path = os.path.expanduser(args.file_path)
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    print(f"\n📁 Processing: {os.path.basename(file_path)}")
    
    ext = Path(file_path).suffix.lower()
    mime_type = MIME_MAP.get(ext, 'application/octet-stream')

    url = f"{args.api_url}/purchase-orders/parse-document"
    
    try:
        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, mime_type)}
            response = requests.post(url, files=files, timeout=60)
            
        response.raise_for_status()
        data = response.json()
        
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print_summary(data)
            
            # Interactive or auto-creation
            mode = data.get("mode", "unknown")
            if mode == "create" and not args.json:
                if args.auto_create:
                    if not args.supplier_id:
                        print("❌ Error: --supplier-id is required with --auto-create")
                    else:
                        create_po(args.api_url, data, args.supplier_id)
                else:
                    print("💡 Tip: Re-run with --auto-create --supplier-id <ID> to import this PO automatically.")
                    answer = input("Would you like to create this PO now? (y/N): ").strip().lower()
                    if answer == 'y':
                        sid = args.supplier_id
                        if not sid:
                            try:
                                sid = int(input("Enter Supplier ID: ").strip())
                            except ValueError:
                                print("❌ Invalid ID.")
                                return
                        create_po(args.api_url, data, sid)
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to the API server at {args.api_url}.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def create_po(api_url, data, supplier_id):
    """Helper to create a PO from extracted data."""
    # This is a simplified version of create_purchase_order
    # It sends the extracted items to the PO creation endpoint
    payload = {
        "supplier_id": supplier_id,
        "currency": data.get("currency", "USD"),
        "shipping_cost": data.get("shipping_cost", 0),
        "tax_amount": data.get("tax_amount", 0),
        "items": []
    }
    
    for item in data.get("items", []):
        pid = item.get("matched_product_id")
        if pid:
            payload["items"].append({
                "product_id": pid,
                "quantity_ordered": item.get("quantity", 0),
                "unit_cost": item.get("unit_cost", 0)
            })
    
    if not payload["items"]:
        print("❌ Error: No items matched to products. Cannot create PO.")
        return

    url = f"{api_url}/purchase-orders/"
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        print(f"✅ PO created successfully! ID: {resp.json().get('id')}")
    except Exception as e:
        print(f"❌ Error creating PO: {str(e)}")

if __name__ == "__main__":
    main()
