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