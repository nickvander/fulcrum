import requests

def test_po():
    # assuming we have a PO
    # let's create one first
    res = requests.get("http://localhost:8000/api/v1/purchase_orders/")
    pos = res.json()
    if pos:
        po_id = pos[-1]['id']
        print(f"Fetching PO {po_id}")
        res2 = requests.get(f"http://localhost:8000/api/v1/purchase_orders/{po_id}")
        po = res2.json()
        for item in po.get('items', []):
            prod = item.get('product')
            if prod:
                print(f"Item Product: {prod.get('name')}, Variants: {prod.get('variants')}")
            else:
                print(f"Item {item['id']} has no product attached in JSON")
    else:
        print("No POs found")

if __name__ == "__main__":
    test_po()
