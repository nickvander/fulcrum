import google.adk
print("google.adk:", dir(google.adk))
try:
    from google.adk import Agent
    print("Agent class found")
except ImportError:
    print("Agent class NOT found in top level")

try:
    from google.adk.models import Claude
    import inspect
    print("Claude init:", inspect.signature(Claude.__init__))
except ImportError:
    print("Claude not found")
except Exception as e:
    print(f"Error inspecting Claude: {e}")
