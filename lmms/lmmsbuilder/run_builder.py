import sys
from lmms_builder.cli import builder_main

if __name__ == '__main__':
    # Patch argv so it simulates "LMMs-builder"
    if not sys.argv[0].endswith("LMMs-builder") and not sys.argv[0].endswith("LMMs-builder.exe"):
        sys.argv[0] = "LMMs-builder"
    builder_main()
