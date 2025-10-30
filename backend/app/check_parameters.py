"""
Check the correct parameter names for Google AI classes
"""
import inspect
from semantic_kernel.connectors.ai.google.google_ai import (
    GoogleAITextEmbedding,
    GoogleAIChatCompletion,
)

print("="*60)
print("GoogleAITextEmbedding.__init__ signature:")
print("="*60)
sig = inspect.signature(GoogleAITextEmbedding.__init__)
print(sig)
print("\nParameters:")
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")
        if param.default != inspect.Parameter.empty:
            print(f"    Default: {param.default}")

print("\n" + "="*60)
print("GoogleAIChatCompletion.__init__ signature:")
print("="*60)
sig = inspect.signature(GoogleAIChatCompletion.__init__)
print(sig)
print("\nParameters:")
for param_name, param in sig.parameters.items():
    if param_name != 'self':
        print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")
        if param.default != inspect.Parameter.empty:
            print(f"    Default: {param.default}")

# Try to get docstrings
print("\n" + "="*60)
print("GoogleAITextEmbedding documentation:")
print("="*60)
if GoogleAITextEmbedding.__init__.__doc__:
    print(GoogleAITextEmbedding.__init__.__doc__)
else:
    print("No docstring available")

print("\n" + "="*60)
print("GoogleAIChatCompletion documentation:")
print("="*60)
if GoogleAIChatCompletion.__init__.__doc__:
    print(GoogleAIChatCompletion.__init__.__doc__)
else:
    print("No docstring available")