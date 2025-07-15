# rthook_shibokensupport_fix.py
import inspect
import sys
import os

# Store the original getsource
_original_getsource = inspect.getsource

def patched_getsource(obj):
    # We only apply the patch if the object's module is related to shibokensupport
    # This prevents breaking other parts of the application that might need inspect.getsource
    if hasattr(obj, '__module__') and obj.__module__ and 'shibokensupport' in obj.__module__:
        try:
            # Try to get the source as normal using the original function
            return _original_getsource(obj)
        except (TypeError, OSError, UnicodeDecodeError) as e:
            # If reading source fails for shibokensupport, return an empty string.
            # This prevents the fatal crash.
            # print(f"DEBUG: Caught {type(e).__name__} for shibokensupport module: {obj.__module__}. Returning empty source.")
            return ""
    # For all other modules, call the original getsource
    return _original_getsource(obj)

# Apply the patch to inspect.getsource
inspect.getsource = patched_getsource

# Additional environment variables for good measure, though the inspect patch is primary.
os.environ['PYSIDE_DISABLE_SIGNATURE'] = '1'
os.environ['PYSIDE_DISABLE_SIGNATURE_LOADING'] = '1'

# Optional: print a message to console to confirm this rthook was applied
# print("PyInstaller shibokensupport UnicodeDecodeError workaround applied via rthook.")