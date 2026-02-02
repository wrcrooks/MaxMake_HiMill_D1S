# MaxMake HiMill D1S
Repository with various files related to the MaxMake HiMill D1(S)

## Table of Contents
### FreeCAD
#### - maxmake_post.py
This file is a FreeCAD Post-Processor meant to be used with the MaxMake HiMill D1(S). I wrote it through reverse-engineering the GCODE commands that the machine expects, as contained in the "factory" `Wood Block-mermaid.nc` demo file.

The Post-Processor can be added to FreeCAD by placing it in the `C:\Program Files\FreeCAD X.X\Mod\CAM\Path\Post\scripts` (Windows) directory, or the equivalent path in Linux or MacOS.

### CNCjs
#### - [README.md](CNCjs/README.md)
This file contains the documentation of my journey using CNCjs to replace the MaxmakeLAB software.

### cncjs-pendant-gamepad-redux
#### - [README.md](cncjs-pendant-gamepad-redux/README.md)

## Hardware
Here is a list of machine-compatible parts that I've found:
### Purchasable
- 3D Probe Attachment:
  - *Note: It seems like the internals of the MaxMake probe are identical to the popular "V6 3D Touch Probe" but I have these parts on order to attempt to repair my broken MaxMake Probe. More info below in the `Lessons Learned` section*
  - [3D Touch Probe Needle Holder](https://www.amazon.com/dp/B0F9PQLWQ6) [**Unconfirmed**]
  - [3D Touch Probe Needle x3](https://www.amazon.com/dp/B0FDL1K7HW) [**Unconfirmed**]
### 3D Printable
- 90-Degree Vacuum Adapter
  - *Note: This adapter is meant to fit into the vacuum port on the back of the HiMill D1(S) and provides the right diameter for a 'DEWALT 6 Gallon STEALTHSONIC Wet Dry Shop Vac' (Part No. DXV06P-QT) to attach on the other end*
  - [HiMill D1(S) 90 Degree Vacuum Adapter](https://www.printables.com/model/1582029-himill-d1s-cnc-90-degree-vacuum-adapter)

## Lessons Learned
I'm fairly new to CNC machining, with most of my pertinent knowledge being around additive manufacturing (3D Printing). Below are some of the things I learned along the way:
- Dropping a 0.8mm end mill toolbit is enough to break it
  - What does this mean for you? 
    - Take care of your toolbits
    - Keep the speeds/feeds low when using such fragile (and relatively cheap) toolbits
    - Use the small diameter toolbits for cleaning up corners and edges, but avoid using them to remove too much material
- I plunged my 3D probe attachment into the machine bed / spoilboard (Z direction)
  - What does this mean for you?
    - Care and intentionality should scale up with the spindle jogging distance. I had my jog distance set to 10mm when I clicked the Z- button instead of the X+ button. Could've been avoided if I took my time
    - When the 3D probe was driven into the machine bed, the probe 'needle' was bent to approximately 90 degrees before the 'needle holder' broke (surprisingly strong plastic). While my first instinct was to buy a new 3D probe attachment (which I did), I disassembled the broken one and found that end of it relatively straightforward... **SIDE-QUEST UNLOCKED** (see `Hardware` section above for more details)