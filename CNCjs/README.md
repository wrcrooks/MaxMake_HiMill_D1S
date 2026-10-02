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
Place the Following in `/etc/systemd/system/cncjs.service`
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
Place the Following in `~/.cncrc`
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
        "toolChangePolicy": 1,
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
        },
        {
            "id": "943a04bc-1067-400c-98b7-b41fafb1dcd7",
            "mtime": 1769985084869,
            "name": "Frame Work Area",
            "content": "; Traverse around the boundary\nG90\nG0 Z10 ; go to z-safe\nG0 X[xmin] Y[ymin]\nG0 X[xmax]\nG0 Y[ymax]\nG0 X[xmin]\nG0 Y[ymin]"
        },
        {
            "id": "d0bb07d5-db19-454a-a25e-311917412dfb",
            "mtime": 1769998363090,
            "name": "Probe X",
            "content": "; X-Probe\nG91\nG38.2 X100 F200\nG90\n; Set the active WCS X0\nG10 L20 P1 X0\n; Retract from the touch plate\nG91\nG0 X-4\nG90"
        },
        {
            "id": "b21396d7-d1ab-4ccc-827b-80cacc2a6969",
            "mtime": 1769998376291,
            "name": "Probe Y",
            "content": "; Y-Probe\nG91\nG38.2 Y100 F200\nG90\n; Set the active WCS Y0\nG10 L20 P1 Y0\n; Retract from the touch plate\nG91\nG0 Y-4\nG90"
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
Place the Following in `/etc/systemd/system/webcamd.service`
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

### Tool Changes (M6)
*Measured on a D1S (GrblHAL 1.1f, `[APP:v1.0.34]`) with CNCjs 1.10.7 and `toolChangePolicy: 1`. Everything below was observed on the serial stream or confirmed with a paper touch-off; the numbers are from my machine.*

`toolChangePolicy: 1` ("Send M6 commands") makes CNCjs forward `M6` to the controller. With the default `0`, CNCjs strips `M6` out of a running program instead. The D1S then runs its own tool change cycle, which does **not** do what CNCjs's own tool change handling would do:

**What `T<n>M6` does on the D1S**
1. **G54 is zeroed immediately** (G54 becomes 0 / 0 / 0). The tool length offset (`TLO`) stays 0 and the tool table (`T:1`..`T:8`) stays 0, so the new tool length is not applied anywhere.
2. It lifts to machine Z0 and moves to the tool change position (machine X140 Y0, the front light glows orange, state `Tool`).
3. After you swap the tool and push the button it moves to the probe (machine X0 Y-7.5), probes twice and reports `[PRB:x,y,z:1]`. The two readings repeat to about 10 µm. `PRB` Z is the machine Z where the tool tip triggered the probe, so a longer tool triggers higher.
4. It ends `Idle` at machine X0 Y-7.5 Z0. It does **not** return to where it was or restore the work zero.

So the work zero has to be rebuilt after every tool change, in Z as well as X/Y.

**Things that bite**
- **`error:47` (`ATC: current tool is not set. Set current tool with M61.`)**: after a power loss the firmware has no current tool and refuses `M6`. Send `M61 Q<n>` with `n` set to the tool in the spindle. `Q0` does not count as set, so use 1 or higher. `$EE` lists the controller's error texts.
- **Stale `G92` offset**: a `G92` offset persists across resets and homing and adds to the work offset (check `$#`; active offset = G54 + G92 + TLO). Mine was left behind by the `G92 X0 Y0 Z0` at the end of a `SAVE_ZERO` macro. Clear it with `G92.1` and do not use `G92` in macros.
- **The measured tool length changes every time a tool is mounted.** Collet seating moved the same tool by up to about 3 mm between mountings. Always re-probe after installing a tool and never reuse a probe value across mountings.
- **Don't drive `M6` from a G-code program.** A `%wait` after `M6` never released (the controller never acknowledged the dwell that `%wait` queues, so CNCjs waited forever), and an `M0` right after `M6` pauses CNCjs (and holds the controller) before the cycle starts. Run `T<n>M6` by hand from the console instead.
- **Don't press Stop in the middle of this.** It soft-resets the controller, which clears `[PRB]` and the firmware's current tool, and it can trigger a pending tool change.

**Procedure**
- *Starting a job:* install the tool, run `T<n>M6` so it gets probed, touch off X/Y/Z on the work (`G10 L20 P1 X0 Y0 Z0`), then run the job.
- *Changing tools mid-job:* pause the job, run `SAVE_BEFORE_M6`, run `T<n>M6` from the console, swap the tool, push the button and wait for the machine to go `Idle`, run `RESTORE_AFTER_M6`, then resume. *(I have only tested the two macros on their own with the machine idle, not with a paused job.)*

**Macros** (create these in the CNCjs Macro widget rather than editing `~/.cncrc`, which CNCjs rewrites). In macros the probe result is `params.PRB.z` (the variable is `params`, not `parameters`).

`SAVE_BEFORE_M6` records the work offset, the tool tip position and the current tool's probe reading:
```
$#
%wait
%global.gx = mposx - posx
%global.gy = mposy - posy
%global.gz = mposz - posz
%global.hx = mposx
%global.hy = mposy
%global.hz = mposz
%global.prb0 = Number(params.PRB.z)
```

`RESTORE_AFTER_M6` rebuilds G54 (Z is shifted by the difference between the new and old probe readings) and returns the tip to where it was:
```
$#
%wait
%dz = Number(params.PRB.z) - global.prb0
G10 L2 P1 X[global.gx] Y[global.gy] Z[global.gz + dz]
G90
G53 G0 X[global.hx] Y[global.hy]
G53 G0 Z[global.hz + dz]
```
*Known quirk: the first `G53` line after the tool change is never acknowledged by the controller (the move still runs), so the macro stalls with one line left in the queue. Pressing **Unlock** (`$X`) in the CNCjs controller panel releases it and the last line runs. A variant that returns with work-coordinate moves instead of `G53` is being tested.*

**Validation:** after each tool change the tip was lowered onto a sheet of paper at the same spot and the DRO read Z0.0 each time (paper touch-off tolerance about ±0.1 mm), with tool length differences between -11.8 and +14.1 mm and different collet seating:

| Change | Probe difference (mm) | DRO Z at paper touch |
|---|---|---|
| T1 to T2 | +14.098 | 0.0 |
| T1 to T2 (after a program Stop and reset) | +13.232 | 0.0 |
| T2 to T1 | -11.840 | 0.0 |
| T1 to T2 | +12.375 | 0.0 |


### Known Issues
- I'm still actively working on how CNCjs interacts with the machine during M6 tool changes. You can track the progress of that quest [here](https://github.com/cncjs/cncjs/discussions/958).

  **Update:** the root cause and a procedure that works are in [Tool Changes (M6)](#tool-changes-m6) above. In short, the D1S zeroes G54 on every `M6` and applies no tool length offset, so the work zero is rebuilt with a pair of macros after each change instead of expecting the machine to restore it. The earlier assumption that the machine restores Work Zero on its own was wrong, so [gcode/tool-change-test.gcode](gcode/tool-change-test.gcode) is superseded and its pass criteria (return to G54 X0/Y0 after each `M6`, `M0` as the resume point) no longer apply.

  **Legacy manual workaround** (`toolChangePolicy: 0`):
  1. Set CNCjs to "Ignore M6 commands (Default)"
  2. Run the GCODE
  3. When the prompt to change the tool comes up in the webpage, issue a `T<x>M6` command in the console (where `<x>` is the tool number in the workplan)
      - The machine should move to the tool change position and the front light should glow orange
  4. Change tool and push the front outer button or internal button to let the machine probe the height of the installed tool
  5. Turn on the spindle to 13000 RPM using the 'M3' button under the 'Spindle' widget
  6. Use the CNCjs UI buttons to jog the tool over to the initial Work Zero point
  7. Once at the Work Zero point, click the Set Zero button (<img width="14px" height="14" src="data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPCEtLSBTdmcgVmVjdG9yIEljb25zIDogaHR0cDovL3d3dy5vbmxpbmV3ZWJmb250cy5jb20vaWNvbiAtLT4KPCFET0NUWVBFIHN2ZyBQVUJMSUMgIi0vL1czQy8vRFREIFNWRyAxLjEvL0VOIiAiaHR0cDovL3d3dy53My5vcmcvR3JhcGhpY3MvU1ZHLzEuMS9EVEQvc3ZnMTEuZHRkIj4KPHN2ZyB2ZXJzaW9uPSIxLjEiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIgeG1sbnM6eGxpbms9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkveGxpbmsiIHg9IjBweCIgeT0iMHB4IiB2aWV3Qm94PSIwIDAgMTAwMCAxMDAwIiBlbmFibGUtYmFja2dyb3VuZD0ibmV3IDAgMCAxMDAwIDEwMDAiIHhtbDpzcGFjZT0icHJlc2VydmUiPgo8bWV0YWRhdGE+IFN2ZyBWZWN0b3IgSWNvbnMgOiBodHRwOi8vd3d3Lm9ubGluZXdlYmZvbnRzLmNvbS9pY29uIDwvbWV0YWRhdGE+CjxnPjxnIHRyYW5zZm9ybT0idHJhbnNsYXRlKDAuMDAwMDAwLDUxMS4wMDAwMDApIHNjYWxlKDAuMTAwMDAwLC0wLjEwMDAwMCkiPjxwYXRoIGQ9Ik00NTQyLjYsNDkyMi4xYy0xMDkzLjEtMTkyLjctMTk1Mi4zLTg2Ny0yMzc5LTE4NjcuOGMtOTIuNC0yMTguMi0xODIuOC01NTQuNC0yMTguMi04MTJjLTMzLjQtMjQ5LjctMTEuOC03ODguNCw0MS4zLTEwMzguMWMxMjkuOC02MDkuNSw0MzQuNS0xMTkzLjQsOTUzLjYtMTgyOC41YzI4My4xLTM0NC4xLDkwOC4zLTEwNTEuOSwxNDY2LjctMTY1OS40YzI1My42LTI3NS4yLDQ5NS40LTUzOC43LDUzOC43LTU4Ny45bDgwLjYtODguNWw0NTIuMiw1MjguOUM3MDEwLTYzOCw3NDE5LTExNyw3NzIzLjcsNDMxLjZjNDQ0LjQsODA2LjEsNTI1LDE1NzYuOCwyNDkuNywyNDA2LjVjLTI5NC45LDg4OC43LTEwMTAuNiwxNjIyLTE4ODcuNSwxOTM0LjZjLTM2My43LDEyOS44LTU0OC41LDE2MS4yLTk5Mi45LDE2OS4xQzQ4MTUuOSw0OTQ1LjcsNDY0NC44LDQ5MzkuOCw0NTQyLjYsNDkyMi4xeiBNNTMzOC45LDMyODguM2M1NzYtMTIxLjksMTAyNC4zLTU1Mi41LDExNzEuOC0xMTMwLjVjNTMuMS0yMDQuNSw1My4xLTUyNS0yLTczNy4zYy0xNzMtNjgyLjItNzc2LjYtMTE1MC4yLTE0ODYuNC0xMTUwLjJjLTkzNS45LDAtMTY1MS41LDg0MS41LTE1MDAuMSwxNzY5LjVjNTEuMSwzMTguNSwxOTYuNiw1OTcuNyw0MzguNCw4MzUuNmMyMjQuMSwyMjAuMiw0NjAuMSwzNTAsNzQ3LjEsNDEyLjlDNDg2OSwzMzIzLjcsNTE2OS44LDMzMjMuNyw1MzM4LjksMzI4OC4zeiIvPjxwYXRoIGQ9Ik0zMDA5LTIwNTEuNmMtMTUxNy44LTIwMC41LTI1NzMuNi01ODkuOC0yODQzLTEwNTEuOWMtMzkxLjItNjY2LjUsOTg5LTEzMjcuMSwzMjQ2LTE1NDkuM2MxMDcxLjUtMTA2LjIsMjQ3MS40LTkwLjQsMzUyOS4xLDM3LjRjNjE3LjQsNzYuNywxMjUyLjQsMjA4LjQsMTcxOC40LDM1Ny44YzUyNC45LDE2OS4xLDgyNS44LDMyNi40LDEwNDcuOSw1NDYuNmMxMTgsMTE4LDE0NS41LDE1Ny4zLDE3MywyNTMuNmM5MC40LDMwOC43LTEzMy43LDU4NS45LTY4Mi4zLDg0NS40Yy01MTEuMiwyNDMuOC0xMzc0LjMsNDYyLTIyMzMuNSw1NjQuM2wtMjAyLjUsMjMuNmwtMTQ1LjUtMTQzLjVjLTgwLjYtODAuNi0xNDMuNS0xNDcuNS0xNDEuNi0xNDkuNGMyLTMuOSwxNjcuMS0xOS43LDM2Ny43LTM3LjRjMTIyNC45LTEwNi4yLDE5NjAuMi0zMjIuNCwyMTE1LjUtNjIxLjNjMTc1LTM0MC4yLTQzMC42LTcwOS44LTE1MTEuOS05MjAuMWMtMTkxMy0zNzMuNi00NjI2LjItMjQzLjgtNTg3MC43LDI4MS4yYy01NzAuMiwyMzkuOS03MTMuNyw1NjAuMy0zNjMuNyw4MTBjMzEyLjYsMjI0LjEsMTE2OS44LDQwNSwyMjE1LjgsNDcxLjlsMjE0LjMsMTMuOGwtMTU1LjMsMTU1LjNjLTgyLjYsODQuNS0xNjEuMiwxNTMuNC0xNzMsMTUxLjRDMzMwMy45LTIwMTIuMywzMTY2LjMtMjAzMS45LDMwMDktMjA1MS42eiIvPjwvZz48L2c+Cjwvc3ZnPgo=" alt="Horizontal Circle w/ Map Pin">) for each axis
  8. Click the Run button in the top center controls to resume
*Note: This manual process can very likely lead to mismatched Work Zeros, so it is far from ideal. Use with caution to avoid breaking toolbits*
