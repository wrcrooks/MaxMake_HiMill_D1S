# CNCjs
## Tutorial
These steps were heavily inspired by the tutorial [here](https://www.apalrd.net/posts/2022/cnc_js/). I went with Debian 13.3 on an x64 platform, but you can also go with Raspbian on a Raspberry Pi 4/5 ARM platform.

### Hardware:
*Note: Links may be out of date*
- **Dell Wyse 5070 or 3040 Thin Client** (Source: eBay)
- **Intel 9560NGW** (Source: [Amazon](https://www.amazon.com/dp/B084TPX75K))
  - *Note: My 5070 did not come with a wireless adapter*
- **MHF4 WLAN Network Adapter Antenna** (Source: [Amazon](https://www.amazon.com/dp/B07QDTXGGJ))
  - *Note: My 5070 did not come with a wireless adapter*
- **Logitech F710 Gamepad** (Source: [Amazon](https://www.amazon.com/dp/B0041RR0TW)) **[Optional]**
  - *Note: See the [cncjs-pendant-gamepad-redux](../cncjs-pendant-gamepad-redux/README.md) file for more notes on this effort*
- **Logitech Brio 101** (Source: [Amazon](https://www.amazon.com/dp/B0BXGFFSL1)) **[Optional]**
- **Portable 15.6 1080p Monitor** (Source: [Amazon](https://www.amazon.com/dp/B0DG84XZYR)) **[Optional]**
- **Monitor Stand Arm** (Source: [Amazon](https://www.amazon.com/dp/B0DX9GMYZM)) **[Optional]**
- **DisplayPort to Mini HDMI Cable** (Source: [Amazon](https://www.amazon.com/dp/B0DBHFBLGD)) **[Optional]**

### Step 1: Install CNCjs
```
# Install
sudo apt install nodejs npm
sudo npm install -g cncjs --unsafe-perms

# Test Installation
cncjs --allow-remote-access -p 8080

# Modify Permissions
sudo setcap CAP_NET_BIND_SERVICE=+eip /usr/bin/node
sudo usermod -a -G <user> discovery

# Set Up CNCjs as a Service
sudo touch /etc/systemd/system/cncjs.service
sudo chmod 664 /etc/systemd/system/cncjs.service
sudo nano /etc/systemd/system/cncjs.service
```
Place the Following in /etc/systemd/system/cncjs.service
```
[Unit]
Description=CNC Controller Web UI
After=network-online.target

[Service]
ExecStart=cncjs -p 80
User=discovery
WorkingDirectory=/home/discovery
Restart=always

[Install]
WantedBy=multi-user.target
```
`Ctrl-C`, `y` key, `ENTER` key

Commands Continued
```
sudo systemctl daemon-reload
sudo systemctl start cncjs
sudo systemctl enable cncjs
sudo mkdir /cncjs
nano ~/.cncrc
```
Place the Following in ~/.cncrc
```
{
    "state": {
        "allowAnonymousUsageDataCollection": false,
        "checkForUpdates": true,
        "controller": {
            "exception": {
                "ignoreErrors": false
            }
        }
    },
    "watchDirectory": "/cncjs",
    "secret": "<secret>",
    "allowRemoteAccess": true,
    "accessTokenLifetime": "365d",
    "tool": {
        "toolChangePolicy": 0,
        "toolChangeX": 0,
        "toolChangeY": 0,
        "toolChangeZ": 0,
        "toolProbeX": 0,
        "toolProbeY": 0,
        "toolProbeZ": 0,
        "toolProbeCustomCommands": "",
        "toolProbeCommand": "G38.2",
        "toolProbeDistance": 1,
        "toolProbeFeedrate": 10,
        "touchPlateHeight": 0
    },
    "commands": [
        {
            "title": "Update (root user)",
            "commands": "sudo npm install -g cncjs@latest --unsafe-perm; pkill -a -f cnc"
        },
        {
            "title": "Update (non-root user)",
            "commands": "npm install -g cncjs@latest; pkill -a -f cnc"
        },
        {
            "title": "Reboot",
            "commands": "sudo /sbin/reboot"
        },
        {
            "title": "Shutdown",
            "commands": "sudo /sbin/shutdown"
        }
    ],
    "macros": [
        {
            "id": "fc1448a2-63db-4019-99df-6be463abc100",
            "mtime": 1769560481437,
            "name": "Tool Change",
            "content": "T1 M06"
        }
    ]
}
```

### Step 2: Set Up Webcam [Optional]
```
# Install
sudo apt install v4l-utils cmake libjpeg62-turbo-dev
git clone https://github.com/jacksonliam/mjpg-streamer
cd mjpg-streamer/mjpg-streamer-experimental
make
sudo make install

# Test Installation
sudo mjpg_streamer -i "input_uvc.so -d /dev/video0 -r 1920x1080" -o "output_http.so -p 8080"

# Set Up MJPG Streamer as a Service
sudo touch /etc/systemd/system/webcamd.service
sudo chmod 664 /etc/systemd/system/webcamd.service
sudo nano /etc/systemd/system/webcamd.service
```
Place the Following in /etc/systemd/system/webcamd.service
```
[Unit]
Description=Webcam Stream
After=network-online.target

[Service]
ExecStart=mjpg_streamer -i "input_uvc.so -d /dev/video0 -r 1920x1080" -o "output_http.so -p 8080"
Restart=always

[Install]
WantedBy=multi-user.target
```
`Ctrl-C`, `y` key, `ENTER` key

Commands Continued
```
sudo systemctl daemon-reload
sudo systemctl start webcamd
sudo systemctl enable webcamd
```