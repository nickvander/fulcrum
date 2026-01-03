try:
    import google.adk.models
    print("google.adk.models:", dir(google.adk.models))
except ImportError as e:
    print(f"Error: {e}")
