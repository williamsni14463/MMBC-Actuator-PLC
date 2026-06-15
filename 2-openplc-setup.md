# OpenPLC Runtime Installation (Raspberry Pi)

## 1. Check Date and Time

After SSH'ing into the Pi, commands may fail if the date and time are incorrect.

Check the current date and time:

```bash
timedatectl
```

If the time is incorrect, manually set it.

Example (June 15, 2026 at 11:15 AM):

```bash
sudo date -s "15 JUN 2026 11:15:00"
```

> Note: It does not need to be accurate to the second. Just get it reasonably close to the current time.

---

## 2. Install OpenPLC Runtime

Once SSH'd into the Pi from your computer, run the following commands **one at a time** and wait for each to finish before running the next:

### Clone OpenPLC Repository

```bash
git clone https://github.com/thiagoralves/OpenPLC_v3.git
```

### Open the Repository

```bash
cd OpenPLC_v3
```

### Run Installation Script

```bash
./install.sh rpi
```

> Installation may take several minutes.

---

## 3. Install OpenPLC Editor (Computer)

Install the **OpenPLC Editor** on your computer (**not the Raspberry Pi**):

https://autonomylogic.com/download

---

## 4. Start OpenPLC Runtime

After installation finishes, go back into the OpenPLC directory:

```bash
cd OpenPLC_v3
```

Start the runtime:

```bash
sudo ./start_openplc.sh
```

---

## 5. Open OpenPLC Runtime in Browser

Open a web browser and navigate to:

```text
https://YOUR_PI_IP_ADDRESS:8080
```

Example:

```text
https://131.xxx.xxx.xxx:8080
```

---

## 6. Login

Default credentials:

**Username**
```text
openplc
```

**Password**
```text
openplc
```

---

## 7. Configure Hardware

After logging in:

1. Navigate to **Hardware**
2. Change hardware to:

```text
Raspberry Pi
```

3. Click **Save Changes**

Your OpenPLC Runtime should now be configured for the Raspberry Pi.
