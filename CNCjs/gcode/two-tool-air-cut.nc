(Exported by FreeCAD)
(Post Processor: maxmake_post)
(Output Time:2026-10-02 21:22:17.063312)
(begin preamble)
(tools in this job: T1 then T2)
(Needs D1S firmware V1.0.38 or later and CNCjs tool change policy Send M6 commands.)
(Before running: install T1. After a power cycle send M61 Q1 first.)
(Send T1M6 and push the button so T1 is probed, then touch off X Y Z and set the zero with G10 L20 P1 X0 Y0 Z0.)
(At each tool change the job stops after probing: swap the tool, push the button, wait for Idle, then press Resume.)
(If it stops again right after you resume, the probe reference is missing: press Stop and do not resume.)
(At the end CNCjs may keep showing the job as running: press Stop once the machine is Idle.)
(begin operation: Tool 1)
(machine: not set, mm/min)
M5
M3
(finish operation: Tool 1)
(begin operation: Square tool 1)
(machine: not set, mm/min)
G0 Z5.000
G0 X10.000 Y10.000
G1 Z3.000 F300.000
G1 X40.000 F600.000
G1 Y40.000
G1 X10.000
G1 Y10.000
G0 Z5.000
(finish operation: Square tool 1)
(tool change to T2)
G0Z5.000S13000
M5
%global.gx = mposx - posx
%global.gy = mposy - posy
%global.gz = mposz - posz
%global.prb0 = 0
%global.prb0 = params.PRB.result === 1 ? Number(params.PRB.z) : 0
%msg [global.prb0 < 0 ? "Tool change to T2 ahead: when the machine stops at the tool change position, swap the tool and push the button. Press Resume only after it has probed the tool and stopped." : "No probe reference: press Stop and probe the tool first"]
[global.prb0 < 0 ? "(probe reference ok)" : "M0"]
T2 M6
M0
%msg [mposx === 0.0 && mposy === -7.5 && mposz === 0.0 ? "" : "Resumed too early: wait until the new tool has been probed and the machine has stopped, then press Resume"]
[mposx === 0.0 && mposy === -7.5 && mposz === 0.0 ? "(new tool probed)" : "M0"]
%msg [mposx === 0.0 && mposy === -7.5 && mposz === 0.0 ? "" : "Resumed too early: wait until the new tool has been probed and the machine has stopped, then press Resume"]
[mposx === 0.0 && mposy === -7.5 && mposz === 0.0 ? "(new tool probed)" : "M0"]
%dz = 0 / 0
%dz = mposx === 0.0 && mposy === -7.5 && mposz === 0.0 && params.PRB.result === 1 && Number(params.PRB.z) < 0 && global.prb0 < 0 ? Number(params.PRB.z) - global.prb0 : 0 / 0
%msg [dz === dz ? "" : "Not safe to continue: the new tool was not probed or the reading is missing. Press Stop and do not resume"]
[dz === dz ? "(probe ok)" : "M0"]
G10 L2 P1 X[global.gx] Y[global.gy] Z[global.gz + dz]
G90
G0 Z[-(global.gz + dz)]
G0 X[10.000 + 0 * dz] Y[10.000 + 0 * dz]
G0 Z[5.000 + 0 * dz]
%global.gz = global.gz + dz
%global.prb0 = Number(params.PRB.z)
(begin operation: Tool 2)
(machine: not set, mm/min)
M3 S13000
(finish operation: Tool 2)
(begin operation: Square tool 2)
(machine: not set, mm/min)
G0 Z5.000
G0 X15.000 Y15.000
G1 Z3.000 F300.000
G1 X35.000 F600.000
G1 Y35.000
G1 X15.000
G1 Y15.000
G0 Z5.000
(finish operation: Square tool 2)
(begin postamble)
G0Z5.000S13000
G0X0.000Y0.000S13000
G0Z5.000
M30
