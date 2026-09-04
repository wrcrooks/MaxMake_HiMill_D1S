; ============================================================
; CNCjs / MaxMake HiMill D1S — M6 Tool Change Validation Test
; ============================================================
; PURPOSE
;   Exercises 3 tool changes (T1/T2/T3 M6) plus a return-to-
;   Work-Zero move after each one, to confirm that:
;     - toolChangePolicy: 1 ("Send M6 commands") is forwarding
;       M6 to the controller and the D1S onboard tool-change /
;       auto-probe cycle fires correctly, and
;     - G90 absolute mode + Work Zero (G54 X0/Y0) survive the
;       round trip through each tool change without drifting.
;
;   The spindle is NEVER commanded on (no M3/M4/M5 anywhere in
;   this file) and every move stays at SAFE_Z, well above any
;   stock/clamps/fixtures. This file only proves out positioning
;   and the M6 handshake — it does NOT validate Z tool-length
;   compensation against real material, since that would require
;   plunging near the work.
;
; BEFORE RUNNING
;   1. Set the Tool widget's Tool Change Policy to "Send M6
;      commands" (toolChangePolicy: 1 in ~/.cncrc).
;   2. Jog to a Work Zero (G54) with generous clearance: nothing
;      -- no clamps, stock, vise, or cables -- within at least
;      30mm in X/Y and below SAFE_Z in Z.
;   3. Edit SAFE_Z and the travel distance below (search for
;      "EDIT ME") to match your actual clearance if 25mm / 15mm
;      is not safe for your current setup.
;   4. Keep a hand on the e-stop for this first run. Watch the
;      first Z lift and first XY move closely before walking away.
;   5. This is loaded and run like any other G-code file (not a
;      CNCjs macro) -- open it in the GCode widget and hit Run.
; ============================================================

G21                       ; units: millimeters
G17                       ; XY plane
G90                       ; absolute positioning
G94                       ; feed per minute

; Rise to safe height first, before any XY travel
G1 Z25 F500               ; EDIT ME: SAFE_Z (mm) -- must clear all fixtures/stock
G1 X0 Y0 F300              ; confirm starting at Work Zero XY
G4 P1

; ---------------- Tool Change 1 ----------------
; Move away from zero so the return move below is a real check
G1 X15 Y15 F300            ; EDIT ME: travel distance (mm), stay within clear area
G4 P1

T1 M6                      ; forwarded to controller -- D1S should move to its
                            ; tool-change position and glow orange

; --- Manual step: change to Tool 1, then push the probe button.
; --- Resume in CNCjs once the D1S finishes probing and goes idle.
M0

G90                        ; reassert absolute mode in case of leftover state
G1 Z25 F500                ; reassert safe height before moving
G1 X0 Y0 F300               ; return-to-zero check: compare DRO to expected X0 Y0
G4 P2

; ---------------- Tool Change 2 ----------------
G1 X-15 Y15 F300
G4 P1

T2 M6

; --- Manual step: change to Tool 2, then push the probe button.
; --- Resume in CNCjs once the D1S finishes probing and goes idle.
M0

G90
G1 Z25 F500
G1 X0 Y0 F300
G4 P2

; ---------------- Tool Change 3 ----------------
G1 X-15 Y-15 F300
G4 P1

T3 M6

; --- Manual step: change to Tool 3, then push the probe button.
; --- Resume in CNCjs once the D1S finishes probing and goes idle.
M0

G90
G1 Z25 F500
G1 X0 Y0 F300
G4 P2

; ============================================================
; Test complete. Spindle was never engaged. If the machine
; never alarmed and the DRO read X0 Y0 (at SAFE_Z) after each
; "return-to-zero check" above, M6 handling under
; toolChangePolicy: 1 is working correctly.
; ============================================================
M2
