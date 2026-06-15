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
- Username: choose something mnemorable like your first name
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

Proceed to https://pingprod.fnal.gov:9031/idp/SSO.saml2?SAMLRequest=nZJBT%2BMwEIX%2FSuR7nTjQVLGaSt1Wq63EQkQKB27GHhdLiZ31OGH3329wiwoHEOJm2W%2FmffPGSxRdm%2Fd8PYQnewt%2FBsCQ%2FO1ai%2Fz4UpHBW%2B4EGuRWdIA8SN6sf1%2FxnGa89y446VqSrBHBB%2BPsxlkcOvAN%2BNFIuLu9qshTCD3yNNXgO0Px%2BGLd8%2BmEVLoutWLsxQGociTZThjGipd%2B5%2Bre2MNkqKi2oqUHN%2FIyu2CpUX3aNDc08pLkp%2FMS4jgV0aJFIMluW5HmeqMkK6TOFqpQlyIvF0UJWmmp5gtdskc5n4RYC0QzwrkUcYCdxSBsqEie5cUsK2Zsvmclzwp%2BUVLGLh9IUp%2BC%2BGGsmjA%2FT%2B3xKEL%2Ba7%2BvZ%2FVNs48NRqPAX0%2FqbwR2Dx5jWFN%2FslrGLHiE92%2FX%2BTmXeN0hWX0FYJm%2BtTmZ9vxlgt22dq2R%2F5J127rnjQcRpqmCHyAuqBPhYxJGWbwxaqajlA8We5BGG1AkXZ1s3%2F%2FZ1X8%3D&RelayState=https%3A%2F%2Ffermi.servicenowservices.com%2Fsaml_redirector.do%3Fsysparm_nostack%3Dtrue%26sysparm_uri%3D%252Fnav_to.do%253Furi%253D%25252Fcom.glideapp.servicecatalog_cat_item_view.do%25253Fsysparm_id%25253Dafd29c2dcc6dcd80f9e6f19b4c359c2a

Log in with Services, then register the Raspberry Pi. Choose Linux as OS, device type as Desktop, and name as Raspberry-Pi-4

---

## 9. SSH

SSH means Secure Shell, and it's a way of controlling a computer remotely. This comes in handy with the Pi because we want to be able to control it remotely from our computer.

After ~5 min, the service desk should have approved the request tpo register the pi on the internet

For Windows, open Windows Powershell and type the following command
For Mac, ⌘ + Space → type Terminal → Enter |or go to| Applications → Utilities → Terminal

```bash
ssh "YOUR-USERNAME"@"PI-IP-ADDRESS"
```
Example: 
username: cole & pi-ip: 131.235.173.216 

```bash
ssh cole@131.235.173.216
```

Success!! You have SSH'd into the Pi (:

