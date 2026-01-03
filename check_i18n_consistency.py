import json
import os
import sys
from typing import Dict, List, Set, Any

def get_all_keys(data: Dict[str, Any], prefix: str = "") -> Set[str]:
    keys = set()
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        keys.add(full_key)
        if isinstance(v, dict):
            keys.update(get_all_keys(v, full_key))
    return keys

def check_duplicates(file_path: str) -> List[str]:
    duplicates = []
    duplicates = []
    
    class DuplicateCheckDecoder(json.JSONDecoder):
        def __init__(self, *args, **kwargs):
            super().__init__(object_pairs_hook=self.dict_with_duplicate_check, *args, **kwargs)

        def dict_with_duplicate_check(self, pairs):
            d = {}
            for k, v in pairs:
                if k in d:
                    duplicates.append(k)
                d[k] = v
            return d

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f, cls=DuplicateCheckDecoder)
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return []
    
    return duplicates

def get_common_strings(data: Dict[str, Any]) -> Dict[str, str]:
    """Returns a map of string value to its key in the 'common' section."""
    common = data.get("common", {})
    return {str(v).lower(): f"common.{k}" for k, v in common.items() if not isinstance(v, dict)}

def find_standardization_candidates(data: Dict[str, Any], common_map: Dict[str, str], prefix: str = "") -> List[str]:
    candidates = []
    for k, v in data.items():
        full_key = f"{prefix}.{k}" if prefix else k
        if full_key.startswith("common"):
            continue
            
        if isinstance(v, dict):
            candidates.extend(find_standardization_candidates(v, common_map, full_key))
        else:
            val_str = str(v).lower()
            if val_str in common_map:
                candidates.append(f"{full_key}: '{v}' could be '{common_map[val_str]}'")
    return candidates

def main():
    # Default to finding all json files in the i18n directory if only one argument is provided
    if len(sys.argv) < 2:
        print("Usage: python3 check_i18n_consistency.py <base_file> [<compare_file1> ...]")
        print("Example: python3 check_i18n_consistency.py frontend/src/assets/i18n/en.json")
        sys.exit(1)

    base_file = sys.argv[1]
    i18n_dir = os.path.dirname(base_file)
    
    if len(sys.argv) == 2:
        # Auto-discover other files in the same directory
        compare_files = [
            os.path.join(i18n_dir, f) 
            for f in os.listdir(i18n_dir) 
            if f.endswith('.json') and os.path.join(i18n_dir, f) != base_file
        ]
    else:
        compare_files = sys.argv[2:]

    if not os.path.exists(base_file):
        print(f"Base file {base_file} not found.")
        sys.exit(1)

    try:
        with open(base_file, 'r', encoding='utf-8') as f:
            base_data = json.load(f)
    except Exception as e:
        print(f"Error loading {base_file}: {e}")
        sys.exit(1)

    base_keys = get_all_keys(base_data)
    common_map = get_common_strings(base_data)

    print(f"--- Analysis of {base_file} ---")
    duplicates = check_duplicates(base_file)
    if duplicates:
        print(f"  [ERROR] [DUPLICATE KEYS FOUND]: {', '.join(duplicates)}")
        # We'll fail at the end if errors are found
    else:
        print("  No duplicate keys found.")

    candidates = find_standardization_candidates(base_data, common_map)
    if candidates:
        print(f"  [WARNING] [STANDARDiZATION CANDIDATES FOUND] ({len(candidates)} items):")
        for c in candidates[:100]: # Show first 100
            print(f"    - {c}")
        if len(candidates) > 100:
            print(f"    ... and {len(candidates) - 100} more.")
    else:
        print("  No redundant common strings found.")

    has_errors = bool(duplicates)

    for comp_file in compare_files:
        if not os.path.exists(comp_file):
            print(f"\n--- Comparison with {comp_file} ---")
            print("  [ERROR] File not found.")
            has_errors = True
            continue

        try:
            with open(comp_file, 'r', encoding='utf-8') as f:
                comp_data = json.load(f)
        except Exception as e:
            print(f"\n--- Comparison with {comp_file} ---")
            print(f"  [ERROR] Error loading file: {e}")
            has_errors = True
            continue

        comp_keys = get_all_keys(comp_data)
        missing_keys = base_keys - comp_keys
        extra_keys = comp_keys - base_keys

        print(f"\n--- Comparison with {comp_file} ---")
        
        comp_duplicates = check_duplicates(comp_file)
        if comp_duplicates:
            print(f"  [ERROR] [DUPLICATE KEYS FOUND]: {', '.join(comp_duplicates)}")
            has_errors = True

        if missing_keys:
            print(f"  [ERROR] [MISSING KEYS] ({len(missing_keys)} items):")
            has_errors = True
            for k in sorted(list(missing_keys))[:10]:
                print(f"    - {k}")
            if len(missing_keys) > 10:
                print(f"    ... and {len(missing_keys) - 10} more.")
        else:
            print("  No missing keys.")

        if extra_keys:
            print(f"  [INFO] [EXTRA KEYS] (In {comp_file} but not in {base_file}):")
            for k in sorted(list(extra_keys))[:5]:
                print(f"    - {k}")

    if has_errors:
        print("\n[RESULT] I18n validation failed. Please fix the errors above.")
        sys.exit(1)
    else:
        print("\n[RESULT] I18n validation passed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
