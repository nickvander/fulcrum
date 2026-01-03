try:
    import google.adk
    print("Found google.adk")
    # print(dir(google.adk)) 
except ImportError as e:
    print(f"Error: {e}")

try:
    import google.generativeai
    print("Found google.generativeai")
except ImportError as e:
    print(f"Error: {e}")
