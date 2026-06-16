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

```bash
ifconfig -a
```
The MAC address would appear under the first column labeled "eth0", it will look like "XX:XX:XX:XX:XX:XX"

---

## 8. Register Pi On Fermilab Wifi

Back on your own computer, proceed to 

https://fermi.servicenowservices.com/kb_view.do?sysparm_article=KB0011206

Under the Register a New Device Instructions, select the link in step #1 to Register / Update / Unregister a Personally Owned Device

Log in with Services, then register the Raspberry Pi. Choose Linux as OS, device type as Desktop, and name as Raspberry-Pi-4

---

## 9. SSH

SSH means Secure Shell, and it's a way of controlling a computer remotely. This comes in handy with the Pi because we want to be able to control it remotely from our computer.

After ~5 min, the service desk should have approved the request to register the pi on the internet

To get the IP address of the Pi, type the following command inside the raspberry pi terminal:

```bash
hostname -I
```
For Windows, open Windows Powershell and type the following command
For Mac, ⌘ + Space → type Terminal → Enter |or go to| Applications → Utilities → Terminal

Then to SSH into the pi, type the following command from your computer terminal.

```bash
ssh "YOUR-USERNAME"@"PI-IP-ADDRESS"
```
Example: 
username: cole & pi-ip: 131.235.173.216 

```bash
ssh cole@131.235.173.216
```

Success!! You have SSH'd into the Pi (:

