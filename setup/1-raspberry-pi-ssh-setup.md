# Raspberry Pi SSH Setup

## 1. Install Raspberry Pi Imager

Download Raspberry Pi Imager here:  
https://www.raspberrypi.com/software/

Install and open the application.

---

## 2. Prepare microSD Card

- Insert microSD card into your computer
- Open Raspberry Pi Imager

---

## 3. Flash Raspberry Pi OS

### Select Operating System

Choose:
- Raspberry Pi OS (64-bit)

### Select Storage

Choose your microSD card

---

## 4. Configure Settings (IMPORTANT)

Before writing, click the gear icon (or "Edit Settings") to configure the Pi before first boot. This saves a lot of hassle.

### General

- Hostname: choose something simple such as "mypi"
- Username: choose something memorable like your first name
- Password: set a memorable password

### Location

- Timezone: `America/Chicago`
- Capital City: Washington, DC

### Network

- SSID: `fgz`
- Network type: Open network

### Services

- Enable SSH

---

## 5. Write to SD Card

Click **Write** and wait:
- ~10–15 minutes
- Includes verification

---

## 6. First Boot

Insert SD card into Raspberry Pi and connect:
- Power
- HDMI
- Keyboard, Mouse

Boot time: ~2–3 minutes

---

## 7. Find MAC Address (WiFi Registration)

Run on the Pi:

```
ifconfig -a
```

The MAC address shows up under the first column labeled "eth0" — it looks like `XX:XX:XX:XX:XX:XX`

---

## 8. Register Pi on Fermilab Wifi

Back on your own computer, go to:

https://fermi.servicenowservices.com/kb_view.do?sysparm_article=KB0011206

Under the Register a New Device Instructions, select the link in step #1 to **Register / Update / Unregister a Personally Owned Device**

Log in with Services, then register the Raspberry Pi:
- OS: Linux
- Device type: Desktop
- Name: Raspberry-Pi-4

---

## 9. SSH into the Pi

SSH (Secure Shell) is how you control the Pi remotely from your computer — super useful since you don't want to have a monitor/keyboard plugged into the Pi forever.

After ~5 minutes, the service desk should have approved the request.

First, find the Pi's IP address by running this in the Pi's terminal:

```
hostname -I
```

Then, on your computer:
- **Windows:** open Windows PowerShell
- **Mac:** `⌘ + Space` → type "Terminal" → Enter, or go to Applications → Utilities → Terminal

Then SSH in:

```
ssh YOUR-USERNAME@PI-IP-ADDRESS
```

Example (username: cole, pi IP: 131.235.173.216):

```
ssh cole@131.235.173.216
```

Success!! You're in 🎉

---

**Next step:** [Install OpenPLC Runtime →](2-openplc-runtime-setup.md)
