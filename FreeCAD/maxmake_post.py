import FreeCAD
from FreeCAD import Units
import Path
import Path.Post.Utils as PostUtils
import argparse
import datetime
import os
import re
import shlex
from PathScripts import PathUtils
import PathScripts.PathUtils as PathUtils
from builtins import open as pyopen

TOOLTIP = """
This is a postprocessor file for the Path workbench. It is used to
take a pseudo-G-code fragment outputted by a Path object, and output
real G-code suitable for the MaxMake HiMill D1(S) CNC Machine.
This postprocessor, once placed in the appropriate PathScripts folder, can be used directly from inside
FreeCAD, via the GUI importer or via python scripts with:

import maxmake_post
maxmake_post.export(object,"/path/to/file.ncc","")

Tool changes (needs D1S firmware V1.0.38 or later and CNCjs toolChangePolicy 1): the D1S
zeroes G54 on every M6 and applies no tool length offset. Each tool change is written as
T<n> M6 followed by M0: the job stops while you swap the tool and push the button, and after
you press Resume, CNCjs-evaluated lines rebuild G54 with the probe difference applied to Z and
return to where the job left off. See CNCjs/README.md.

With --split-files every tool change starts a new file instead (<name>_01_T1.nc, ...) and
the work zero is rebuilt by hand with the SAVE_BEFORE_M6 / RESTORE_AFTER_M6 macros.
"""

now = datetime.datetime.now()

parser = argparse.ArgumentParser(prog="linuxcnc", add_help=False)
parser.add_argument("--no-header", action="store_true", help="suppress header output")
parser.add_argument("--no-comments", action="store_true", help="suppress comment output")
parser.add_argument("--line-numbers", action="store_true", help="prefix with line numbers")
parser.add_argument(
    "--no-show-editor",
    action="store_true",
    help="don't pop up editor before writing output",
)
parser.add_argument("--precision", default="3", help="number of digits of precision, default=3")
parser.add_argument(
    "--preamble",
    help='set commands to be issued before the first command, default="G17\nG90"',
)
parser.add_argument(
    "--postamble",
    help='set commands to be issued after the last command, default="M05\nG17 G90\nM2"',
)
parser.add_argument(
    "--inches", action="store_true", help="Convert output for US imperial mode (G20)"
)
parser.add_argument(
    "--modal",
    action="store_true",
    help="Output the Same G-command Name USE NonModal Mode",
)
parser.add_argument("--axis-modal", action="store_true", help="Output the Same Axis Value Mode")
parser.add_argument(
    "--split-files",
    action="store_true",
    help="write one file per tool and leave the tool change to the CNCjs macros",
)

TOOLTIP_ARGS = parser.format_help()

# These globals set common customization preferences
OUTPUT_COMMENTS = True
OUTPUT_HEADER = True
OUTPUT_LINE_NUMBERS = False
SHOW_EDITOR = True
MODAL = False  # if true commands are suppressed if the same as previous line.
OUTPUT_DOUBLES = True  # if false duplicate axis values are suppressed if the same as previous line.
COMMAND_SPACE = " "
LINENR = 100  # line number starting value

# These globals will be reflected in the Machine configuration of the project
UNITS = "G21"  # G21 for metric, G20 for us standard
UNIT_SPEED_FORMAT = "mm/min"
UNIT_FORMAT = "mm"

MACHINE_NAME = "not set"
CORNER_MIN = {"x": 0, "y": 0, "z": 0}
CORNER_MAX = {"x": 1000, "y": 600, "z": 300}
PRECISION = 3

# Globals to maintain progress throughout GCODE generation (reset at the start of every export)
TOOL_CHANGE_INDEX = 0

# parse() leaves this marker where an M6 was; export() splits the output into one file per tool there
TOOL_CHANGE_MARKER = "@@TOOLCHANGE %d@@\n"
TOOL_CHANGE_MARKER_RE = r"@@TOOLCHANGE (\d+)@@\n"

# CNCjs macros that rebuild the work zero around a tool change (see CNCjs/README.md)
SAVE_MACRO = "SAVE_BEFORE_M6"
RESTORE_MACRO = "RESTORE_AFTER_M6"

# One file with in-program tool changes (default), or one file per tool (--split-files)
SPLIT_FILES = False

# Machine position where the D1S's tool change cycle always ends (its tool probe, raised to Z0).
# CNCjs reaches the M0 after T<n> M6 long before the machine does, so the restore only goes
# ahead once the machine is actually there, i.e. the new tool has been probed.
PROBE_END_MPOS = (0.0, -7.5, 0.0)

# Last X/Y written (output units) and the X/Y in effect at each tool change, so the job can
# return there afterwards. Reset at the start of every export.
LAST_XY = [None, None]
TOOL_CHANGE_POSES = []

# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """"""
DEFAULT_PREAMBLE = PREAMBLE

# Postamble text will appear following the last operation. Retracts to the machine top
# (G53 G0 Z0) rather than a work Z, so it is safe wherever the work zero was set.
POSTAMBLE = """G53 G0 Z0
G0 X0.000 Y0.000
M30
"""
DEFAULT_POSTAMBLE = POSTAMBLE

# Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# Post operation text will be inserted after every operation
POST_OPERATION = """"""

# Tool Change commands are written before each tool change: retract to the machine top
# (G53 G0 Z0, safe wherever the work zero was set) and stop the spindle.
TOOL_CHANGE = """G53 G0 Z0
M5
"""

# Tool Change commands will be inserted after a tool change
# POST_TOOL_CHANGE = """M3"""


def processArguments(argstring):
    global OUTPUT_HEADER
    global OUTPUT_COMMENTS
    global OUTPUT_LINE_NUMBERS
    global SHOW_EDITOR
    global PRECISION
    global PREAMBLE
    global POSTAMBLE
    global UNITS
    global UNIT_SPEED_FORMAT
    global UNIT_FORMAT
    global MODAL
    global OUTPUT_DOUBLES
    global SPLIT_FILES

    # FreeCAD keeps this module loaded between exports, so start from the defaults every time;
    # otherwise an option given once (e.g. --split-files) silently applies to later exports.
    OUTPUT_HEADER = True
    OUTPUT_COMMENTS = True
    OUTPUT_LINE_NUMBERS = False
    SHOW_EDITOR = True
    PREAMBLE = DEFAULT_PREAMBLE
    POSTAMBLE = DEFAULT_POSTAMBLE
    UNITS = "G21"
    UNIT_SPEED_FORMAT = "mm/min"
    UNIT_FORMAT = "mm"
    MODAL = False
    OUTPUT_DOUBLES = True
    SPLIT_FILES = False

    try:
        args = parser.parse_args(shlex.split(argstring))
        if args.no_header:
            OUTPUT_HEADER = False
        if args.no_comments:
            OUTPUT_COMMENTS = False
        if args.line_numbers:
            OUTPUT_LINE_NUMBERS = True
        if args.no_show_editor:
            SHOW_EDITOR = False
        print("Show editor = %d" % SHOW_EDITOR)
        PRECISION = args.precision
        if args.preamble is not None:
            PREAMBLE = args.preamble
        if args.postamble is not None:
            POSTAMBLE = args.postamble
        if args.inches:
            UNITS = "G20"
            UNIT_SPEED_FORMAT = "in/min"
            UNIT_FORMAT = "in"
            PRECISION = 4
        if args.split_files:
            SPLIT_FILES = True
        if args.modal:
            MODAL = True
        if args.axis_modal:
            OUTPUT_DOUBLES = False

    except (SystemExit, Exception) as e:  # argparse exits on bad arguments
        print("maxmake_post: could not use the arguments %r: %s" % (argstring, e))
        return False

    return True


def export(objectslist, filename, argstring):
    if not processArguments(argstring):
        return None
    global UNITS
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT

    for obj in objectslist:
        if not hasattr(obj, "Path"):
            print(
                "the object " + obj.Name + " is not a path. Please select only path and Compounds."
            )
            return None

    print("postprocessing...")
    global TOOL_CHANGE_INDEX
    global LINENR
    global now
    TOOL_CHANGE_INDEX = 0  # state from a previous export in this session must not leak in
    LINENR = 100
    now = datetime.datetime.now()
    LAST_XY[:] = [None, None]
    del TOOL_CHANGE_POSES[:]

    head = ""

    # write header
    if OUTPUT_HEADER:
        head += linenumber() + "(Exported by FreeCAD)\n"
        head += linenumber() + "(Post Processor: " + __name__ + ")\n"
        head += linenumber() + "(Output Time:" + str(now) + ")\n"

    # Write the preamble
    if OUTPUT_COMMENTS:
        head += linenumber() + "(begin preamble)\n"
    for line in PREAMBLE.splitlines(False):
        head += linenumber() + line + "\n"
    # head += linenumber() + UNITS + "\n"

    # Every tool change (M6) starts a new file. Text before the first tool change is kept
    # in `prefix`; each later piece is a [tool number, text] entry in `sections`.
    prefix = [""]
    sections = []

    def add(text):
        if sections:
            sections[-1][1] += text
        else:
            prefix[0] += text

    for obj in objectslist:

        # fetch machine details
        job = PathUtils.findParentJob(obj)

        myMachine = "not set"

        if hasattr(job, "MachineName"):
            myMachine = job.MachineName

        if hasattr(job, "MachineUnits"):
            if job.MachineUnits == "Metric":
                UNITS = "G21"
                UNIT_FORMAT = "mm"
                UNIT_SPEED_FORMAT = "mm/min"
            else:
                UNITS = "G20"
                UNIT_FORMAT = "in"
                UNIT_SPEED_FORMAT = "in/min"

        # do the pre_op
        begin = ""
        if OUTPUT_COMMENTS:
            begin += linenumber() + "(begin operation: %s)\n" % comment_text(obj.Label)
            begin += linenumber() + "(machine: %s, %s)\n" % (
                myMachine,
                UNIT_SPEED_FORMAT,
            )
        for line in PRE_OPERATION.splitlines(True):
            begin += linenumber() + line

        # parse() returns [text, tool, text, tool, text, ...] once split on its tool change markers
        parts = re.split(TOOL_CHANGE_MARKER_RE, parse(obj))
        if parts[0] == "" and len(parts) > 1:
            # this object is the tool change itself: its "begin operation" comment belongs in the new file
            sections.append([int(parts[1]), ""])
            add(begin + parts[2])
            rest = parts[3:]
        else:
            add(begin + parts[0])
            rest = parts[1:]
        for i in range(0, len(rest), 2):
            sections.append([int(rest[i]), ""])
            add(rest[i + 1])

        # do the post_op
        post = ""
        if OUTPUT_COMMENTS:
            post += linenumber() + "(finish operation: %s)\n" % comment_text(obj.Label)
        for line in POST_OPERATION.splitlines(True):
            post += linenumber() + line
        add(post)

    # do the post_amble
    postamble = ""
    if OUTPUT_COMMENTS:
        postamble += "(begin postamble)\n"
    for line in POSTAMBLE.splitlines(True):
        postamble += linenumber() + line

    # The program has to state its units: the controller does not follow FreeCAD's settings.
    head += linenumber() + UNITS + "\n"

    if len(sections) > 1 and not SPLIT_FILES:
        # The tool change block rebuilds G54 from machine positions reported in mm, and only G54.
        body = prefix[0] + "".join(text for _, text in sections)
        if UNITS != "G21":
            print("maxmake_post: tool changes inside the program only work in mm; use --split-files or metric output")
            return None
        other = re.search(r"^(N\d+ )?(G5[5-9](\.\d)?)\b", body, re.M)
        if other:
            print(
                "maxmake_post: this job uses work offset %s; tool changes inside the program only work"
                " with G54. Use G54 or --split-files." % other.group(2)
            )
            return None

    # Assemble the output: one file with in-program tool changes, or one file per tool
    if not sections:
        tools = [None]
        texts = [head + prefix[0] + postamble]
    elif not SPLIT_FILES:
        tools = [None]
        text = head + job_banner([tool for tool, _ in sections]) + prefix[0] + sections[0][1]
        for i in range(1, len(sections)):
            text += tool_change_block(i, sections[i][0], TOOL_CHANGE_POSES[i]) + sections[i][1]
        texts = [text + postamble]
    else:
        tools = [tool for tool, _ in sections]
        texts = []
        for i, (tool, body) in enumerate(sections):
            text = head + tool_banner(i, len(sections), tool)
            if i == 0:
                text += prefix[0]
            text += body
            if i < len(sections) - 1:
                text += section_end(sections[i + 1][0])
            else:
                text += postamble
            texts.append(text)

    paths = output_paths(filename, tools)

    if len(texts) == 1 and FreeCAD.GuiUp and SHOW_EDITOR:
        dia = PostUtils.GCodeEditorDialog()
        dia.editor.setText(texts[0])
        result = dia.exec_()
        if result:
            texts[0] = dia.editor.toPlainText()

    print("done postprocessing.")

    if not filename == "-":
        for path, text in zip(paths, texts):
            gfile = pyopen(path, "w")
            gfile.write(text)
            gfile.close()
        if len(paths) > 1:
            print("Tool changes are done by hand, so one file was written per tool:")
            for path in paths:
                print("  " + path)

    return "".join(texts)


def output_paths(filename, tools):
    """One path when there is a single output, otherwise <name>_<nn>_T<tool>.<ext> in run order."""
    if len(tools) == 1:
        return [filename]
    base, ext = os.path.splitext(filename)
    return ["%s_%02d_T%d%s" % (base, i + 1, tool, ext) for i, tool in enumerate(tools)]


def tool_banner(index, total, tool):
    """Comment block at the top of each file: which tool, and what to do before running it.

    Plain comments only: no parentheses or square brackets inside (CNCjs evaluates square
    brackets and Grbl comments end at the first closing parenthesis).
    """
    out = linenumber() + "(file %d of %d: tool T%d)\n" % (index + 1, total, tool)
    if not OUTPUT_COMMENTS:
        return out
    if index == 0:
        lines = [
            "Install T%d and send T%dM6 from the console so it is probed." % (tool, tool),
            "Then touch off X Y Z on the work and set the zero with G10 L20 P1 X0 Y0 Z0.",
            "Do not press Stop or reset after this: that clears the probe reference.",
        ]
    else:
        lines = [
            "Before this file, with the previous tool still in the spindle:",
            "1 run the %s macro" % SAVE_MACRO,
            "2 send T%dM6 from the console, swap the tool, push the button, wait for Idle" % tool,
            "3 run the %s macro, press Unlock if it stalls" % RESTORE_MACRO,
            "Then run this file.",
        ]
    for line in lines:
        out += linenumber() + "(" + line + ")\n"
    return out


def section_end(next_tool):
    """End of a file that is followed by a tool change: retract, spindle off, end of program."""
    out = ""
    if OUTPUT_COMMENTS:
        out += linenumber() + "(end of file: next tool is T%d)\n" % next_tool
    for line in TOOL_CHANGE.splitlines(True):
        out += linenumber() + line
    out += linenumber() + "M30\n"
    return out


def job_banner(tools):
    """Comment block at the top of a single-file job with in-program tool changes.

    Plain comments only: no parentheses or square brackets inside (CNCjs evaluates square
    brackets and Grbl comments end at the first closing parenthesis).
    """
    out = linenumber() + "(tools in this job: %s)\n" % " then ".join("T%d" % t for t in tools)
    if not OUTPUT_COMMENTS:
        return out
    first = tools[0]
    lines = [
        "Needs D1S firmware V1.0.38 or later and CNCjs tool change policy Send M6 commands.",
        "Before running: install T%d. After a power cycle send M61 Q%d first." % (first, first),
        "Send T%dM6 and push the button so T%d is probed, then touch off X Y Z and set the zero with G10 L20 P1 X0 Y0 Z0."
        % (first, first),
        "At each tool change the job stops after probing: swap the tool, push the button, wait for Idle, then press Resume.",
        "If it stops again right after you resume, the probe reference is missing: press Stop and do not resume.",
        "At the end CNCjs may keep showing the job as running: press Stop once the machine is Idle.",
    ]
    for line in lines:
        out += linenumber() + "(" + line + ")\n"
    return out


def tool_change_block(index, tool, pose):
    """In-program tool change: retract, T<n> M6, M0, then rebuild G54 and return over `pose`.

    The tool goes back to the X/Y it left from but stays at the machine top; the next
    operation's own moves bring it down, at heights the CAM job already made safe.

    The % and [ ] lines are evaluated by CNCjs when it sends them, so they run after the M0
    once the cycle has finished and CNCjs has parsed the new [PRB] reading. They must start
    in column 1 and never get a line number. If the probe reference is missing, a line turns
    into M0 and stops the job before anything that depends on it is sent.

    CNCjs's evaluator is not JavaScript: && does not short-circuit (params.PRB.z throws when
    there is no reading, and the assignment is then skipped) and NaN is not a known name.
    So each value is first reset to a safe one (0, or 0 / 0 for NaN) and then assigned in a
    form that throws, leaving the safe value in place, when the reading is missing.
    """
    x, y = [0.0 if v is None else v for v in pose]
    fmt = "." + str(PRECISION) + "f"
    out = ""
    if OUTPUT_COMMENTS:
        out += linenumber() + "(tool change to T%d)\n" % tool
    for line in TOOL_CHANGE.splitlines(True):
        out += linenumber() + line
    if index == 1:
        # G54 offset as set by the touch-off, and the first tool's probe reading as reference.
        # mpos - pos is the work offset, which stays valid while earlier moves are still queued.
        out += "%global.gx = mposx - posx\n"
        out += "%global.gy = mposy - posy\n"
        out += "%global.gz = mposz - posz\n"
        out += "%global.prb0 = 0\n"
        out += "%global.prb0 = params.PRB.result === 1 ? Number(params.PRB.z) : 0\n"
    msg = (
        "Tool change to T%d ahead: when the machine stops at the tool change position, swap the tool and push"
        " the button. Press Resume only after it has probed the tool and stopped." % tool
    )
    out += '%%msg [global.prb0 < 0 ? "%s" : "No probe reference: press Stop and probe the tool first"]\n' % msg
    out += '[global.prb0 < 0 ? "(probe reference ok)" : "M0"]\n'
    out += linenumber() + "T%d M6\n" % tool
    out += linenumber() + "M0\n"
    # Resume pressed before the cycle has finished: stop again before the restore is evaluated.
    # Checked twice, so it takes two early presses to get past it.
    at_probe = "mposx === %s && mposy === %s && mposz === %s" % tuple(repr(float(v)) for v in PROBE_END_MPOS)
    for _ in range(2):
        out += (
            '%%msg [%s ? "" : "Resumed too early: wait until the new tool has been probed and the machine has'
            ' stopped, then press Resume"]\n' % at_probe
        )
        out += '[%s ? "(new tool probed)" : "M0"]\n' % at_probe
    # The shift is only valid once the machine is back at the probe: if Resume got past both
    # checks above anyway, dz stays NaN and the job stops below instead of using the old reading.
    out += "%dz = 0 / 0\n"
    out += (
        "%%dz = %s && params.PRB.result === 1 && Number(params.PRB.z) < 0 && global.prb0 < 0"
        " ? Number(params.PRB.z) - global.prb0 : 0 / 0\n" % at_probe
    )
    out += (
        '%msg [dz === dz ? "" : "Not safe to continue: the new tool was not probed or the reading is missing.'
        ' Press Stop and do not resume"]\n'
    )
    out += '[dz === dz ? "(probe ok)" : "M0"]\n'
    out += "G10 L2 P1 X[global.gx] Y[global.gy] Z[global.gz + dz]\n"
    out += linenumber() + "G90\n"
    out += "G0 Z[-(global.gz + dz)]\n"
    out += "G0 X[%s + 0 * dz] Y[%s + 0 * dz]\n" % (format(x, fmt), format(y, fmt))
    out += "%global.gz = global.gz + dz\n"
    out += "%global.prb0 = Number(params.PRB.z)\n"
    return out


def comment_text(text):
    """Text safe inside a G-code comment: Grbl ends a comment at the first ')', and CNCjs
    evaluates anything in square brackets."""
    return re.sub(r"[()\[\]]", "", str(text))


def linenumber():
    global LINENR
    if OUTPUT_LINE_NUMBERS is True:
        LINENR += 10
        return "N" + str(LINENR) + " "
    return ""


def parse(pathobj):
    global PRECISION
    global MODAL
    global OUTPUT_DOUBLES
    global UNIT_FORMAT
    global UNIT_SPEED_FORMAT
    global TOOL_CHANGE_INDEX

    out = ""
    lastcommand = None
    precision_string = "." + str(PRECISION) + "f"
    currLocation = {}  # keep track for no doubles

    # the order of parameters
    # linuxcnc doesn't want K properties on XY plane  Arcs need work.
    params = [
        "X",
        "Y",
        "Z",
        "A",
        "B",
        "C",
        "I",
        "J",
        "F",
        "S",
        "T",
        "Q",
        "R",
        "L",
        "H",
        "D",
        "P",
    ]
    firstmove = Path.Command("G0", {"X": -1, "Y": -1, "Z": -1, "F": 0.0})
    currLocation.update(firstmove.Parameters)  # set First location Parameters

    if hasattr(pathobj, "Group"):  # We have a compound or project.
        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(compound: " + pathobj.Label + ")\n"
        for p in pathobj.Group:
            out += parse(p)
        return out
    else:  # parsing simple path

        # groups might contain non-path things like stock.
        if not hasattr(pathobj, "Path"):
            return out

        # if OUTPUT_COMMENTS:
        #     out += linenumber() + "(" + pathobj.Label + ")\n"

        for c in PathUtils.getPathWithPlacement(pathobj).Commands:

            outstring = []
            command = c.Name
            outstring.append(command)

            # if modal: suppress the command if it is the same as the last one
            if MODAL is True:
                if command == lastcommand:
                    outstring.pop(0)

            if c.Name[0] == "(" and not OUTPUT_COMMENTS:  # command is a comment
                continue

            # Now add the remaining parameters in order
            for param in params:
                if param in c.Parameters:
                    if param == "F" and (
                        currLocation[param] != c.Parameters[param] or OUTPUT_DOUBLES
                    ):
                        if c.Name not in [
                            "G0",
                            "G00",
                        ]:  # linuxcnc doesn't use rapid speeds
                            speed = Units.Quantity(c.Parameters["F"], FreeCAD.Units.Velocity)
                            if speed.getValueAs(UNIT_SPEED_FORMAT) > 0.0:
                                outstring.append(
                                    param
                                    + format(
                                        float(speed.getValueAs(UNIT_SPEED_FORMAT)),
                                        precision_string,
                                    )
                                )
                        else:
                            continue
                    elif param == "T":
                        outstring.append(param + str(int(c.Parameters["T"])))
                    elif param == "H":
                        outstring.append(param + str(int(c.Parameters["H"])))
                    elif param == "D":
                        outstring.append(param + str(int(c.Parameters["D"])))
                    elif param == "S":
                        outstring.append(param + str(int(c.Parameters["S"])))
                    else:
                        if (
                            (not OUTPUT_DOUBLES)
                            and (param in currLocation)
                            and (currLocation[param] == c.Parameters[param])
                        ):
                            continue
                        else:
                            pos = Units.Quantity(c.Parameters[param], FreeCAD.Units.Length)
                            outstring.append(
                                param + format(float(pos.getValueAs(UNIT_FORMAT)), precision_string)
                            )

            # store the latest command
            lastcommand = command
            currLocation.update(c.Parameters)
            if command in ("G0", "G00", "G1", "G01", "G2", "G02", "G3", "G03", "G73", "G81", "G82", "G83", "G85", "G86", "G89"):
                for i, axis in enumerate(("X", "Y")):
                    if axis in c.Parameters:
                        pos = Units.Quantity(c.Parameters[axis], FreeCAD.Units.Length)
                        LAST_XY[i] = float(pos.getValueAs(UNIT_FORMAT))

            # Check for Tool Change:
            if command == "M6":
                # M6 is never written to the G-code: the D1S zeroes G54 in its own cycle and a
                # program cannot drive it safely. Leave a marker so export() starts a new file here.
                # The tool controller's own spindle command (e.g. M3 S13000) follows and is kept,
                # so the speed is set for every tool, the first one included.
                marker = TOOL_CHANGE_MARKER % int(c.Parameters.get("T", 0))
                TOOL_CHANGE_POSES.append(tuple(LAST_XY))
                out += marker
                if TOOL_CHANGE_INDEX == 0:
                    out += linenumber() + "M5\n"
                TOOL_CHANGE_INDEX += 1
                continue
            
            if command == "G54":
                return ""

            if command == "message":
                if OUTPUT_COMMENTS is False:
                    continue
                outstring.pop(0)  # remove the command

            # prepend a line number and append a newline
            if len(outstring) >= 1:
                if OUTPUT_LINE_NUMBERS:
                    outstring.insert(0, (linenumber()))

                # append the line to the final output
                for w in outstring:
                    out += w + COMMAND_SPACE
                out = out.strip() + "\n"
            
            # # Check for Tool Change:
            # if command == "M6":
            #     # if OUTPUT_COMMENTS:
            #     #     out += linenumber() + "(begin toolchange)\n"
            #     for line in POST_TOOL_CHANGE.splitlines(True):
            #         out += linenumber() + line
            #     out += "(TOOL CHANGE POST)\n"

        return out
