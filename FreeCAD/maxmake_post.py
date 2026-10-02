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

Tool changes: the D1S zeroes G54 on every M6 and applies no tool length offset, and a
running program cannot safely drive its tool change cycle, so M6 is never written to the
G-code. Instead every tool change starts a new file (<name>_01_T1.nc, <name>_02_T2.nc, ...)
and each file begins with a comment block listing the steps to take before running it
(the SAVE_BEFORE_M6 / RESTORE_AFTER_M6 macros, see CNCjs/README.md).
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

# Preamble text will appear at the beginning of the GCODE output file.
PREAMBLE = """"""

# Postamble text will appear following the last operation.
POSTAMBLE = """G0Z5.000S13000
G0X0.000Y0.000S13000
G0Z5.000
M30
"""

# Pre operation text will be inserted before every operation
PRE_OPERATION = """"""

# Post operation text will be inserted after every operation
POST_OPERATION = """"""

# Tool Change commands are written at the end of the file that precedes a tool change
TOOL_CHANGE = """G0Z5.000S13000
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
        if args.modal:
            MODAL = True
        if args.axis_modal:
            print("here")
            OUTPUT_DOUBLES = False

    except:
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
    TOOL_CHANGE_INDEX = 0  # state from a previous export in this session must not leak in

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
            begin += linenumber() + "(begin operation: %s)\n" % obj.Label
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
            post += linenumber() + "(finish operation: %s)\n" % obj.Label
        for line in POST_OPERATION.splitlines(True):
            post += linenumber() + line
        add(post)

    # do the post_amble
    postamble = ""
    if OUTPUT_COMMENTS:
        postamble += "(begin postamble)\n"
    for line in POSTAMBLE.splitlines(True):
        postamble += linenumber() + line

    # Assemble one output per tool (a single output when the job has no tool change)
    if not sections:
        tools = [None]
        texts = [head + prefix[0] + postamble]
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

            # Check for Tool Change:
            if command == "M6":
                # M6 is never written to the G-code: the D1S zeroes G54 in its own cycle and a
                # program cannot drive it safely. Leave a marker so export() starts a new file here.
                marker = TOOL_CHANGE_MARKER % int(c.Parameters.get("T", 0))
                if TOOL_CHANGE_INDEX == 0:
                    TOOL_CHANGE_INDEX += 1
                    return out + marker + "M5\nM3\n"
                TOOL_CHANGE_INDEX += 1
                out += marker
                continue
            
            if command == "G54":
                return ""

            if command == "message":
                if OUTPUT_COMMENTS is False:
                    out = []
                else:
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
