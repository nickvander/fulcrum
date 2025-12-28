#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

def create_global_test_user(token, country_id):
    """Creates a Global Selling (CBT) test user."""
    url = "https://api.mercadolibre.com/users/global_selling_test_user"
    data = {
        "site_id": "CBT",
        "country_id": country_id
    }
    return _make_request(url, token, data)

def create_marketplace_test_user(token, site_id):
    """Creates a Marketplace test user (e.g., MLM)."""
    url = "https://api.mercadolibre.com/users/test_user"
    data = {
        "site_id": site_id
    }
    return _make_request(url, token, data)

def _make_request(url, token, data):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode('utf-8'), 
            headers=headers, 
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            if response.status != 201 and response.status != 200:
                print(f"Error: Received status code {response.status}", file=sys.stderr)
                return None
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        print(e.read().decode('utf-8'), file=sys.stderr)
        return None
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        return None

def main():
    parser = argparse.ArgumentParser(description="Create MercadoLibre Test Users")
    parser.add_argument("--token", help="MercadoLibre Access Token (can also be set via ML_ACCESS_TOKEN env var)")
    parser.add_argument("--type", choices=["global", "local"], default="local", help="Type of test user to create")
    parser.add_argument("--site", default="MLM", help="Site ID for local user (default: MLM)")
    parser.add_argument("--country", default="US", help="Country ID for global user (default: US)")
    
    args = parser.parse_args()
    
    token = args.token or os.environ.get("ML_ACCESS_TOKEN")
    if not token:
        print("Error: Access Token is required. Provide --token or set ML_ACCESS_TOKEN env var.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Creating {args.type} test user...")
    
    if args.type == "global":
        result = create_global_test_user(token, args.country)
    else:
        result = create_marketplace_test_user(token, args.site)
        
    if result:
        print("\nSUCCESS: Test user created successfully!")
        print(json.dumps(result, indent=2))
        print("\nIMPORTANT: Save these credentials immediately. They cannot be retrieved later.")
        print("-" * 50)
        print(f"User ID:  {result.get('id')}")
        print(f"Username: {result.get('nickname')}")
        print(f"Password: {result.get('password')}")
        print(f"Email:    {result.get('email')}")
        print("-" * 50)

if __name__ == "__main__":
    main()
