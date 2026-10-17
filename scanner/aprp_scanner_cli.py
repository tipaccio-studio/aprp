"""Entry script for PyInstaller (it can't freeze a package's __main__ directly)."""
from aprp_scanner.__main__ import main

raise SystemExit(main())
