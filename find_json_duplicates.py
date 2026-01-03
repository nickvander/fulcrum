import json
import sys

def find_duplicate_keys(json_path):
    print(f"Checking {json_path} for duplicate keys...")
    
    def dict_detect_duplicates(ordered_pairs):
        d = {}
        for k, v in ordered_pairs:
            if k in d:
                print(f"  [DUPLICATE] Key: '{k}'")
            d[k] = v
        return d

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json.load(f, object_pairs_hook=dict_detect_duplicates)
    except Exception as e:
        print(f"  [ERROR] {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_json_duplicates.py <path_to_json>")
        sys.exit(1)
    
    for path in sys.argv[1:]:
        find_duplicate_keys(path)
