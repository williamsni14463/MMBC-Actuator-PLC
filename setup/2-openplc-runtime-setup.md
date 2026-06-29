# OpenPLC Runtime Installation (Raspberry Pi)

> Make sure you've completed [SSH setup](1-raspberry-pi-ssh-setup.md) first and can SSH into the Pi.

---

## 1. Check Date and Time

After SSH'ing in, some commands will fail if the Pi's date/time is wrong (especially `git clone`).

Check it:

```
timedatectl
```

If it looks wrong, set it manually. Example (June 15, 2026 at 11:15 AM):

```
sudo date -s "15 JUN 2026 11:15:00"
```

> Doesn't need to be exact to the second — just close enough.

---

## 2. Install OpenPLC Runtime (on the Pi)

Run these commands **one at a time** and wait for each to finish:

### Clone the repository

```
git clone https://github.com/thiagoralves/OpenPLC_v3.git
```

### Navigate into it

```
cd OpenPLC_v3
```

### Run the install script

```
./install.sh rpi
```

> This takes several minutes — let it finish before moving on.

---

## 3. Install OpenPLC Editor (on your computer)

Install the OpenPLC **Editor** on your computer (not the Pi):

https://autonomylogic.com/download

---

## 4. Start the Runtime

Once installation finishes, go back into the OpenPLC directory:

```
cd OpenPLC_v3
```

Start it:

```
sudo ./start_openplc.sh
```

---

## 5. Open the Runtime in a Browser

Open a browser on your computer and go to:

```
http://YOUR_PI_IP_ADDRESS:8080
```

Example:
```
http://131.xxx.xxx.xxx:8080
```

---

## 6. Log In

Default credentials:

- **Username:** `openplc`
- **Password:** `openplc`

---

## 7. Configure Hardware

After logging in:

1. Navigate to **Hardware**
2. Change hardware to: `Raspberry Pi`
3. Click **Save Changes**

> **Note:** If you're planning to use SPI devices (like a MAX31865 sensor), do NOT set this to "Raspberry Pi" — it hijacks the SPI pins and breaks your sensor. See [Known Issues](../issues/KNOWN_ISSUES.md) for details. For pure GPIO/LED projects, "Raspberry Pi" is fine.

---

**Next step:** [Run the example PLC program →](3-example-raspberry-pi-plc.md)
