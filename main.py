# -*- coding: utf-8 -*-
"""شطرنج کلاسیک و Random Chess — اجرای بازی"""

import sys

try:
    import pygame  # noqa: F401
except ImportError:
    print('ERROR: pygame is not installed.  Run:  pip install -r requirements.txt')
    sys.exit(1)

from ui import run

if __name__ == '__main__':
    run()
