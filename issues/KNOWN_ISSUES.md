# Known Issues & Fixes

A quick-reference collection of bugs and gotchas I've run into. The full diagnostic writeups live in the experiment logs.

---

## Issue #1 — SPI sensor breaks when OpenPLC starts (GPIO conflict)

**Affects:** Any experiment using SPI devices (MAX31865, etc.) on the Pi while OpenPLC Runtime is also running.

**Symptom:** Sensor readings are fine until you hit "Start PLC" in the OpenPLC web UI. The moment the PLC starts, SPI sensors report garbage values (0 Ω, -242°C for PT100). Stopping the PLC doesn't help — only a full power cycle restores normal readings.

**Root cause:** Setting the OpenPLC hardware layer to "Raspberry Pi" forces a hardcoded pin assignment the moment the PLC starts. It reassigns GPIO 5, 9, 10, 11 to digital inputs and GPIO 7, 8 to digital outputs — which happens to completely destroy the SPI0 bus that the MAX31865 uses. This happens regardless of what your PLC program actually does.

**Fix:**
1. OpenPLC Web UI → **Settings → Hardware**
2. Change from **Raspberry Pi** to **Blank for Linux**
   - ⚠️ Pick the **Linux** variant specifically. The generic "Blank" compiles for Windows and breaks things differently.
3. Restart the runtime.

**Full writeup:** [experiments/RND_pt100_openplc_progress_log.md → Issue #1](../experiments/RND_pt100_openplc_progress_log.md#8-issue-log)

---

## Issue #2 — Response time readings cluster in 0–20ms with no resolution

**Affects:** `openplc-response-time-test.md` button timing experiment.

**Symptom:** All 50 timing measurements bunch up between 0–20ms with high variance. Can't tell what the real response time is.

**Root cause:** The default OpenPLC scan/cycle time is ~20ms. Since the PLC logic only updates once per scan, every timing measurement gets quantized to 20ms chunks — like trying to measure seconds with a clock that only has a minute hand.

**Fix:** Reduce the PLC cycle time in the runtime settings. I've gotten it under 1ms successfully. Haven't found the absolute floor yet — more testing needed.

**Full writeup:** [experiments/openplc-response-time-test.md → Issue Log](../experiments/openplc-response-time-test.md#5-issue-log)

---

## Issue #3 — `pip install` fails on Raspberry Pi OS Bookworm

**Symptom:** Running `pip3 install some-package` gives an "externally managed environment" error and refuses to install.

**Root cause:** Raspberry Pi OS Bookworm added a pip guard to prevent system Python packages from being broken by pip installs.

**Fix (option 1):** Add `--break-system-packages` flag:
```
pip3 install --break-system-packages some-package
```

**Fix (option 2):** Use a virtual environment:
```
python3 -m venv my-env
source my-env/bin/activate
pip install some-package
```

If you go the venv route, remember to activate it every time you open a new terminal before running any scripts:
```
source my-env/bin/activate
```

---

## Issue #4 — `git clone` fails or hangs after SSH

**Symptom:** `git clone` hangs or gives certificate/date errors right after SSH'ing into the Pi.

**Root cause:** The Pi's date and time are wrong. This breaks HTTPS certificate validation.

**Fix:**
```
timedatectl           # check what the Pi thinks the time is
sudo date -s "15 JUN 2026 11:15:00"   # set it manually if wrong
```

Doesn't need to be exact — just close enough that TLS handshakes work.

---

## Issue #5 — `.st` file is hard to find when uploading to the runtime

**Symptom:** After building in OpenPLC Editor, can't find the `.st` file to upload.

**Fix:** Navigate to:
```
Your Project Folder → build → OpenPLC Runtime v3 → src → program_name.st
```

Also: don't save your OpenPLC Editor project in OneDrive — it causes path issues during the upload step.
