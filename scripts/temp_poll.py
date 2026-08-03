#!/usr/bin/env python3
"""
temp_poll.py — print the Cernox temperature every 10 seconds.
Uses ls240_driver.py (must be in the same folder). Ctrl-C to stop.
"""

import time
from datetime import datetime
from ls240_driver import LakeShore240

CHANNEL = 1
INTERVAL = 10  # seconds

ls = LakeShore240()
print(f"polling channel {CHANNEL} every {INTERVAL}s — Ctrl-C to stop\n")
try:
    while True:
        k = ls.kelvin(CHANNEL)
        o = ls.ohms(CHANNEL)
        stamp = datetime.now().strftime("%H:%M:%S")
        if k is not None:
            print(f"{stamp}   {k:.3f} K   {k-273.15:.2f} C   {o:.3f} ohm")
        else:
            print(f"{stamp}   <no reading>")
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print("\nstopped")
finally:
    ls.close()