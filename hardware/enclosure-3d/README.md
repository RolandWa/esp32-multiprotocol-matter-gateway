# 3D-printed enclosure, rev03 CONCEPT DRAFT (for the owner's acceptance, not test-printed)

**Status 2026-11-27: every file in `stl/` and `preview/*_rev03.png` is a DRAFT for the owner's acceptance of the concept ("concept first, files second",
`../../docs/ENCLOSURE_3D.md` section 2 item 1).** Nothing was printed, assembled with real boards, measured thermally, measured for RF, or simulated for airflow.
What *was* done is listed in section 8. Do not print the set before the owner has accepted the concept and answered the questions of section 9;
the fit samples (section 5) may be printed earlier. rev01 (104 x 98.8 x 24 mm, screws) was removed on 2026-11-27 at the owner's request; rev02 (74.6 x 69.5 x 30.5 mm,
two USB notches in the top face, dust plug, pin holes) is no longer committed: its STLs lived in `stl/archive_rev02/` (git-ignored, may exist on the owner's disk only) and its previews were deleted - **do not print it**.

The owner's checklist `wytyczne_projektowania_druk3d (1).md` is authoritative; `../../docs/ENCLOSURE_3D.md` section 3a holds the owner's requirements R1-R17.
No PCB exists: two XIAO modules and a BME680 board are hand-wired. **No screw closes the case or holds a board** (the only screws are the two wall screws of R4).

**Assumed mounting orientation (a reading the owner has only partly confirmed):** the case hangs VERTICALLY on a wall or cabinet; the BME680 is at the BOTTOM,
the host's USB-C cable hangs straight DOWN. If the case lies flat, the vents and the opening must be redone.

> **To confirm before anything is printed: the device name.** The owner typed `esp32-matter-gatway`. The design uses **`esp32-matter-gateway`** ("gateway"); it is one parameter
> (`name_l1` / `name_l2` / `name_l3` in `params.scad`) and the name sample (`fit_sample_name_rev03.stl`) shows it in three embolden variants.

## 1. The concept in one picture and in numbers

```text
 FRONT VIEW, lid off, case hanging on the wall.  Seen from the front X runs right to left: the HOST is on the viewer's RIGHT.
 +----------------------------------------------------------------------------+  top face: CLOSED (no slot, no USB notch)
 |  A | .--------------------. |  | .----------------. outlet louvres,    | A  |  A = adhesive FPC antenna on the inside of each end wall,
 |  N | | C6 (USB-C up,      | |  | |                |  angled down       | N  |      10.5 mm from the board edge
 |  T | |  closed ceiling)   | |D | |   (free air    |                    | T  |
 |    | '--------------------' |I | |    ~42 mm,     |                    |    |  D = vertical divider with two wire slots
 |  ^ |   ^ air from the end   |V | |    chimney)    |                    |  ^ |      (sealed with foam after wiring)
 |  | |   | gap over the baffle|  | |                |                    |  | |
 |====+=[ baffle 2 + 3 air + 2 ]=|  | |                |                    |====|  <- end gap (7 mm) beside the large-X wall only
 |    |      ^                  |  | '----------------'                    |    |
 |    | .--------------------.  |  | .----------------.                    |    |
 |    | | BME680 (25.5 x     |  |  | | HOST S3, upside|                    |    |
 |    | |  17.6), upstream   |  |  | | down: USB-C end|                    |    |
 |    | '--------------------'  |  | | DOWN           |                    |    |
 +----+-----[ 4 inlet louvres ]-+--+-+--[ USB opening + 2 tie slots ]------+----+  bottom face: the ONLY opening for the cable, faces DOWN
```

Back plate (not drawn): 2 keyhole chambers, 2 countersunk wall-screw holes, a tape recess, six release slots for the hooks (all blind). Lid (not drawn): two groups of
outlet louvres, the engraved name in three lines in the middle, six hooks on the inner face. **No** USB opening elsewhere, **no** pin holes, **no** inlet in the lid.

Preview images (`preview/`, all `rev03`): `section_front_rev03.png`, `section_side_rev03.png`, `section_plan_rev03.png` (three sections), `view_3d_rev03.png` (base with boards, lid),
`outer_front_34_rev03.png`, `outer_back_rev03.png`, `outer_exploded_rev03.png`, `outer_bottom_rev03.png` (USB opening and inlet louvres), `outer_front_straight_rev03.png`
(straight-on view with the engraved name), `name_proof_rev03.png` (the name probed from the saved lid STL, as seen from the front).

| | rev02 (archived) | **rev03 concept** |
|---|---|---|
| Outer size (X x Z x Y, mounted) | 74.6 x 69.5 x 30.5 mm | **78.8 x 69.5 x 30.5 mm** (base 27.5 deep + lid 3.0): +4.2 mm wide |
| Antenna centre distance | 70.9 mm | **75.1 mm** (owner's floor 60 mm) |
| Patch to nearest board metal (keep-out) | 10.5 mm | **10.5 mm** (assumed 10 mm; RF unmeasured) |
| USB-C openings | 2 (top face, host and C6) + dust plug | **1** (bottom face, host only), lead-in, 2 tie slots; no plug part |
| Openings in the top face | 2 | **0** |
| BOOT/RESET pin holes in the lid | 4 | **0** |
| Inlets in the lid | 2 low louvre groups | **0** (air enters from below only) |
| Engraved name | none | **`esp32-matter-gateway`**, 3 lines, 0.6 mm deep, outer face of the lid |
| Lid joint, boards | 6 hooks, 12 clip arms, no screws | unchanged (hooks moved to the new divider position) |
| Volume of printed parts | base 40 + lid 15 cm3 | base 40.9 + lid 16.1 cm3 |

### The hard part: host USB-C at the bottom against "sensor at the bottom, upstream of the heat"

The two wishes compete for the same corner of the case: the host's USB-C must point down through the bottom wall (so the cable hangs straight), and the BME680 should stand
at the bottom with the modules' heat rising away from it. Candidates, with numbers computed from `params.scad` (A is built and checked; B and C are paper estimates from the same
parameters, not modelled):

| | **A: two columns (chosen)** | B: three columns in one row | C: C6 above the host, sensor alone |
|---|---|---|---|
| Arrangement | host column (host upside down, USB-C down) / divider / sensor + C6 column (BME680 at the bottom, baffle, C6 above) | host, sensor, C6 side by side | host with the C6 stacked above it / divider / sensor column |
| Outer size | **78.8 x 69.5 x 30.5** | about 100-104 wide x about 57 high | about 78.8 x 69.5 (same width: the 25.5 mm BME board sets the column) |
| Antenna centre distance | 75.1 mm | about 96 mm | about 75 mm |
| Keep-out patch to board | 10.5 mm | 10.5 mm | 10.5 mm |
| Sensor upstream of the heat | **yes, upstream of the C6**; the host (hottest) has its own inlet and its exhaust never passes the sensor | no chimney at all: nothing is above or below the sensor, all three sit in one row | the sensor column has no heat source above it, but its air reaches **neither** board |
| Cable / wire routes | host to C6 wires up the free strip beside the host, through divider slot 2; BME wires through slot 1; both U.FL cables 32-37 mm of 100 | long runs across 100 mm | host to C6 wires short, BME wires cross the divider |
| 5 V / UART / EN / BOOT | one bundle, 59 mm | about 40 mm but crossing the sensor | short |
| Host heat path | host column, own outlet in the lid (free air above the host about 42 mm: headroom wasted, a chimney) | host column | host plume rises through the C6 (the C6 sits in the host's exhaust) |

**Why A won.** B is the widest by about 22-25 mm and has no chimney, so R1 and R2 both lose. C keeps the width and puts the C6 into the host's exhaust, and the sensor's air reaches
neither board, so it meets R2 in neither reading. A keeps the sensor physically below and upstream of the C6 (R2 as the owner described it for that board), keeps the host's heat
in its own column, and costs 4.2 mm of width.

**What gives in A, exactly:**
1. **Width: +4.2 mm** (74.6 to 78.8 mm). The BME680 board (25.5 mm) is wider than a XIAO (17.78 mm); its column sets the width, not the antenna floor.
2. **R2 is relaxed, not met in full:** the sensor is upstream of the C6 only. The host takes its air from its own bottom inlet (the USB opening); it does not breathe air that passed the sensor.
   The owner's phrase "from the sensor to both boards" is therefore met for one board of two.
3. **About 42 mm of free air above the host** (the host column is as tall as the C6 column but holds only one board). It is not wasted entirely - it is the host's chimney - but it is volume the
   owner wanted removed.
4. **Cable anchor is outside, not inside** (R13): a clamp strictly inside the case cannot take a tug because the cable leaves through the opening; two tie slots beside the opening
   anchor the cable to the case from below, end arms stop the host board, and the plug (USB-C retention) is the weakest link by design. Section 3.
5. **The antenna keep-out stays 10.5 mm** (not the sketch's 3 mm): RF risk, unmeasured. Antenna distance 75.1 mm.

**Thermal risk, stated plainly.** The hottest module (the host with Wi-Fi/BLE and the Matter stack; its dissipation is unmeasured, I assume some hundred milliwatts) stands in the column right beside the
sensor column, separated by a 2 mm divider that has two wire slots; if the slots are not sealed, the flood fill shows host column and sensor zone connected (check "divider slots open").
The divider conducts a little heat; PETG is a poor conductor but not an insulator. The lid outlets (88 mm2 per column) are smaller than the inlets (300 and 255 mm2), so they set the flow; a
chimney of 60 mm height drives very little air. **Nothing here is a thermal result.** Proposed measurement (`../../docs/TESTING.md` section 6, line "BME680 self-heating"): log the BME680 temperature
and a reference thermometer outside the case for 90 minutes after power-on in four runs - host only (C6 unplugged), host + C6, host + C6 with all vents taped, host + C6 with the divider slots open;
the offset (case sensor minus reference) and its drift show whether the layout works. Pass criterion to be set by the owner; as a starting point I suggest at most 2 K at steady state and no steps when the host's Wi-Fi bursts.
If the offset is too large, the first remedies are: seal the slots better, correct the temperature in firmware, move the sensor to an external lead (outside this concept).

## 2. Requirements R1-R17: met in rev03?

| # | Requirement | Status | How / what is missing |
|---|---|---|---|
| R1 | smaller, narrower | **met, with a stated limit** | 78.8 x 69.5 x 30.5 mm (rev01 104 x 98.8 x 24; rev02 74.6 wide). Width set by the BME680 column; antenna distance 75.1 mm, floor 60 mm |
| R2 | chimney, divider, sensor upstream | **partly** | sensor upstream of the C6 only; the host has its own inlet and its exhaust never passes the sensor (flood fill: host column and sensor zone separate when the slots are sealed, connected when open). Section 1. No airflow or temperature simulated or measured |
| R3 | dust-safe vents | **met in geometry** | inlets in the bottom wall (4 louvre rows, face down) and the USB opening (face down); outlets in the lid angled down; **top face closed** (probe: 0 openings); sides 0; no inlet in the lid. Slots 2.0 mm. No coarse mesh seat |
| R4 | keyholes, tape recess, screws from the back | **met** | unchanged: 2 keyholes in sealed chambers, 2 countersunk wall-screw holes with 1.0 mm skin, tape recess in 2 cells; flood fill: 0 back-face openings connected to the interior |
| R5 | dust plug | **superseded by R13** | the C6 has no opening and the host's opening carries the cable; `usb_dust_plug` and its fit sample are deleted |
| R6 | antennas inside, parametric seat | **met** | unchanged seats on both end walls; BOM / Seeed A-02 / A-01 re-checked with `--antenna-size`; cables re-routed (C6: over the corner clips and down the end gap, 37 mm of 100) |
| R7 | carried over | **met, two changes** | pin holes removed (R16); label recess replaced by the engraved name (R15) |
| R8 | snap-fits, released from the back | **met in geometry, strength not tested** | unchanged hooks (strain 0.56 %), now on the divider and end walls at the new positions; section 4 |
| R9 | rounded shape | **partly** | unchanged: R5 corners, 45 degree chamfers; no bulge |
| R10 | boards without screws, snaps invisible | **met in geometry** | probe of every outer face: front = outlet louvres and the engraved name only; top none; bottom = inlet louvres + the USB opening + 2 tie slots; sides none; back = six release slots + keyholes |
| R11 | strain proof | **met by calculation** | hook / clip geometry unchanged: `tests/unit/test_snap_strain.py` green (25 tests); fatigue not tested |
| R12 | service model, 12 closings | **recorded, consistent** | the case is not opened in normal use; the lid is closed with the cable plugged; the Wi-Fi update path it relies on is not implemented yet |
| R13 | one USB opening, host only, facing down | **met, with a compromise** | one 14 mm opening in the bottom wall, lead-in 1.5 mm at 45 degrees, receptacle path free; the C6 faces a closed ceiling; top face closed; cable anchor = two tie slots (outside the board outline) + end arms; **not** an inside clamp (section 1) |
| R14 | bench use with the lid off | **met, now checked** | the clip check is run on the BASE alone (lip 0.09 mm above the PCB); BOOT/RESET buttons reachable directly; antennas in seats of the base |
| R15 | engraved name | **met in geometry** | `esp32-matter-gateway` in three lines, Bahnschrift Bold (system font), recess 0.6 mm with stepped 45 degree edges, plate 2.4 mm left, strokes >= 2 mm at the floor, >= 3 mm from every louvre, whole text inside the plate; proof image from the STL. **"gateway" to be confirmed** |
| R16 | no BOOT/RESET holes | **met** | probe: the lid is solid in front of all four buttons; no lid inlet stands in front of a button any more |
| R17 | hanging holes on ONE horizontal line + drilling marks | **met in geometry** | keyholes at the same height, 36.0 mm apart, symmetric; dimension line + 2 extension lines + "36 mm" recessed 0.4 mm in the back face (probed); tape cells now end at z = 30 (the marks sit above them); wall-screw hole 1 moved to z = 17 |

## 3. Layout, air path, assembly

Side section (Y = depth, wall on the left): back plate 3.5 | standoff 15.1 (wires, header room, air behind the boards) | PCB 1.6 | parts 3.3 | lid gap 4.0 | lid 3.0.
Air: **in** through 4 louvre rows in the bottom wall under the BME680 (face down) and through the USB opening under the host; **up** through the sensor zone, **over** the baffle through the 7 mm gap beside
the large-X wall (the only way up from the sensor), past the C6, **out** through the lid louvres above the C6 (angled down). The host's air goes up its own column and out through the lid louvres above the host.

**Assembly (case on the wall FIRST, boards after):**
1. Screw the empty base to the wall (countersunk holes: pierce the 1.0 mm skin with the screw), or hang it on two screws in the keyholes (both on one horizontal line, 36 mm apart, symmetric about the centre; the spacing is printed on the back), or use the tape cells.
2. Glue the antennas into the seats (feed end down), route the cables.
3. Solder the wires (5 V / GND / UART / EN / BOOT between host and C6 through divider slot 2; 3V3 / GND / SDA / SCL to the BME680 through slot 1), then **seal both slots with foam or silicone** (this is what keeps the host's warm air out of the sensor zone).
4. Press each board into its four clips from the front (the host **upside down**, USB-C end down; the C6 USB-C up), plug the U.FL connectors.
5. Plug the USB-C cable into the host **from below** (the cable hangs straight down), thread a cable tie through the two tie slots and round the cable, tighten it (the tie head stays inside, so this step is done with the lid still off).
6. Close the lid by pressing it on: six hooks click.

**Disassembly consequence the owner accepted (R8, R12):** the hooks are released from the BACK (blade through the release slots in the back plate, first piercing the 1.0 mm skin), so **the case has to come off the wall to be opened**;
after the first release tape over the slots. To change the cable the tie has to be cut (it is a consumable); the cable can be unplugged and plugged with the lid closed. The C6's USB-C and BOOT/RESET are reached only in a failure: case off the wall, open from the back, lift the board out.

**Cable anchor (R13), what it does and does not do:** a tug on the cable is taken by the tie, which pulls on the slots in the bottom wall, not on the board. The host board is also stopped by its two lower end arms
(0.3 mm gap), so it cannot be pulled out of its clips downwards. The USB-C plug itself still sits in the receptacle: retention is a property of the USB-C connector, **not measured**.

## 4. Snap-fits (R8) and board clips (R10)

**Lid hooks:** 6 cantilever hooks stand on the lid's inner face (beam 1.8 x 4.5 x 19.0 mm, head protrusion 1.0 mm, lead-in 30 degrees, **catch face 45 degrees**), they click behind 45-degree wedge bumps on the divider (2) and on the
end walls (4, two per wall, below the antenna zone). Everything is inside the case; the release slots (2.6 x 3.9 mm blind pockets under each head) are on the back face only. Geometry and strain are the rev02 values; only the
x position of the two divider hooks follows the new divider (`x_div`).

* **Print orientation (chosen deliberately):** the lid prints OUTER face down, so the hooks stand vertically: the bending stress runs along the layer-stacking direction, the weaker one. Printing a hook lying down is not possible
  without supports because its catch face would be a horizontal overhang. The numbers use the **Z** data of the Bambu Lab PETG Basic datasheet V3.0 (ISO 527, typical values, not guaranteed):
  E = 2550 MPa, tensile strength 35 MPa, elongation at break 5.2 % (XY: 2780 MPa, 51 MPa, 9.5 %).
* **No supports:** catch faces 45 degrees, lead-in faces up, bump undersides 45 degrees; tips 1.2 mm flat so no wedge is thinner than 0.8 mm.
* **Calculation** (cantilever, `assembly_check.py` sweeps the real STL for the deflection): the hook must deflect 0.75 mm to close; strain = 1.5 * delta * t / L^2 = **0.56 %** (design limit 0.8 %, about 1/6 of the Z break elongation -
  a design choice, not a tested limit); stress = E * strain = 14 MPa = **41 %** of the Z tensile strength. At rest the hooks are NOT deformed (play 0.15 mm), so there is no creep load.
  The same calculation is repeated independently, for the chosen geometry and for every fit-sample variant, by `tests/unit/test_snap_strain.py` (requirement R11). Estimated forces per hook with an **assumed** friction coefficient 0.3:
  closing 1.9 N, pulling the lid off 3.4 N; six hooks about 20 N. **Not measured.**
* If the fit sample shows the hooks crack or are too loose, the numbers to change are `snap_t`, `snap_h`, `snap_b`, `snap_o` in `params.scad`.

**Service life (R12):** every hook and clip must survive 12 closings (about 10 during commissioning, about 2 later); the case is not opened in normal use; the printed cycle test below uses 20 (a margin of 1.7), nothing more is required.

**Board clips:** each XIAO sits on 4 corner supports (behind the PCB corners) and between 4 flexible arms (1.6 x 3.4 mm, 16.8 mm long, root at the back plate). Each arm ends in a lip that overhangs the PCB corner by 0.7 mm,
0.10 mm above the board (no pressure at rest, the board can lift only by that play). Insertion deflection 0.60 mm -> strain **0.51 %**; about 2.1 N per lip to pull a board out (assumed friction, not measured). The lips sit in the four PCB corners only: no pressure on the U.FL pads,
the buttons or the USB-C shell (nearest keep-out, the RESET button, 0.75 mm away - from Seeed's S3 design file; the C6 is assumed equal, the BME680's corners are unknown). With the lid off (R14) the base alone holds the boards.

## 5. Files, commands, fit samples

| File | Content |
|---|---|
| `params.scad` | the only place with dimensions (each line has its source or `ASSUMED - verify`) |
| `enclosure.scad` | OpenSCAD geometry of all parts |
| `build.py` | **one command regenerates every STL and runs the mesh checker:** `py -3.12 hardware/enclosure-3d/build.py` (about 6 minutes, dominated by the lid with the text and the name sample; OpenSCAD 2021.01; `build.py lid` builds one part) |
| `mesh_check.py` | numpy-only STL checker (closed mesh, degenerate faces, 240 mm, wall thickness, overhang, bridges as inscribed-circle span) |
| `assembly_check.py` | assembled model: collisions, clearances, cables, antenna zone, the USB opening and cable anchor, snap hooks, board clips (base only), visible-face probe, engraved name, no pin holes, air-path flood fill; `--png`, `--hdr 8.5`, `--antenna-size A02` (or `A01`), `--no-air` |
| `layer_check.py`, `render_preview.py`, `render_outer.py`, `scadparams.py` | layer-section pre-check (shapely), section and 3D PNGs, outside renders (pyvista), parameter reader (`--table`, `--assumed`) |
| `stl/` | `enclosure_base_rev03.stl`, `enclosure_lid_rev03.stl`, `fit_sample_{modules,antenna,name,snap,louvre,mount}_rev03.stl`; only the latest revision is committed (an `archive_rev02/` folder may exist locally, git-ignored, not for printing) |

Tests: `py -3.12 -m pytest tests/unit/test_enclosure_meshes.py -q` (skips when `stl/` is empty; `archive_*` folders are ignored by the STL tests; the rev02 mutation tests use a local `stl/archive_rev02/` and skip when it is missing, so a clean checkout runs without them).

**CAD route: OpenSCAD.** Its CGAL kernel is exact, so the saved STL is closed by construction, and `params.scad` is read by both OpenSCAD and the Python checks. No STEP is produced (no PCB, no vendor models).

**Font (R15):** `Bahnschrift:style=Bold`, a Windows system font (NOT bundled: another machine needs the font or the text changes; the committed STLs are unaffected). Chosen because Liberation Sans Bold closed the aperture of the "e" (read as "o") once the 0.8 mm closing and the 45 degree growth were applied. Size 10, letter spacing 1.2, outline shift 0.0 mm per side (widest layer = 0.5 mm; above about 0.4 the "e" starts to close - judged on renders, to be confirmed on the print with `fit_sample_name`, variants -0.1 / 0.0 / +0.1), line pitch 12 mm,
three lines (`esp32-` / `matter-` / `gateway`) because 20 characters in one line cannot be 2 mm strokes on a 78.8 mm wide lid. **Mirroring:** the recess is cut in the lid's outer face, which prints face down; the text is built in the
reader's orientation and mapped with the same transform as the lid (X runs right to left seen from the front), so the saved STL has it mirrored in the print frame and correct on the finished lid; `name_proof_rev03.png`
probes the saved lid STL and draws it as the viewer sees it. **Stepped round edge:** three 0.2 mm layers with the outline offset by 0.35 / 0.55 / 0.75 mm (walls at 45 degrees, no overhang).

**Print settings (all parts: Bambu Lab H2D, 0.4 mm nozzle, Textured PEI, Bambu PETG Basic white, 0.2 mm layers, 4 walls, ~30 % infill, supports none):**

| Part | Orientation (fixed by the STL) | Notes |
|---|---|---|
| `enclosure_base_rev03.stl` | back face on the plate, open front up; 78.8 x 69.5 x 27.5 mm | baffle, divider, hook bumps, clip arms are vertical; louvres 50 degrees; the USB opening is open towards the lid side (no bridge) |
| `enclosure_lid_rev03.stl` | **outer face on the plate**, six hooks stand up from the inner face; 78.8 x 69.5 x 25.9 mm | the engraved name is the first three layers of the plate side (smooth 0.12 mm profile only if you accept the look); hooks: slow |
| `fit_sample_modules` | as in the base | 3 cradles: clearance 0.15 / 0.30 / 0.45 with lip overhang 0.5 / 0.7 / 0.9; USB opening widths 13 / 14 / 15 |
| `fit_sample_snap` | case piece as in the base, lid piece outer face down | 3 hooks with head protrusion 0.8 / 1.0 / 1.2 on the real wall, bump and release slot |
| `fit_sample_name` | 3 plates outer face down | the word "gateway" with embolden 0.10 / 0.25 / 0.40 mm: pick the one that reads best and keeps the strokes clean |
| `fit_sample_antenna` | wall strip on a foot plate | seat depth 0.2 / 0.3 / 0.4 for the chosen patch size |
| `fit_sample_louvre` | standing wall | louvre angle 45 / 50 / 55 (the 55 variant is flagged by the layer check on purpose) |
| `fit_sample_mount` | plate as in the base back | sealed keyhole chamber, skin hole, tape cells 6.5 / 8.0 / 9.5 mm (bridge test) |

`fit_sample_plug` and `usb_dust_plug` no longer exist (R13). One material for the whole set; samples from the same filament.
**Snap test the owner should do (my recommendation, no standard cited): at least 20 close/open cycles on each of the three hook variants with the real release blade, look for white stress marks or cracks, then leave the closed sample 24 hours
and check that the hooks still click; the same 20 cycles pressing a real XIAO into the three cradle variants.** Log the choice:

| Date | Sample | Variant chosen | Filament | Remarks |
|---|---|---|---|---|
| (not printed yet) | | | | |

## 6. Dimensions and sources (key numbers; the full table: `py -3.12 scadparams.py --table`)

| Item | Value | Source |
|---|---|---|
| XIAO outline 17.78 x 21.14 mm, PCB 1.6 mm | | bare-PCB STEP and Seeed's own XIAO ESP32-S3 KiCad design file (the C6 assumed equal; Seeed wiki "21 x 17.8 mm") |
| U.FL (4.54 / 1.73 mm), RESET (3.05 mm), BOOT (14.73 mm), buttons 1.65 mm from the USB end | | Seeed's design file for the S3; **C6 ASSUMED equal** |
| USB-C 9.0 mm wide, 1.5 mm overhang | | repo kicad_mod; height 3.2 and top height 3.3 **ASSUMED**; plug overmould in the 14 x 8 mm opening **ASSUMED** (12.4 x 6.5 mm) |
| Antennas | BOM 39.6 x 8.4 x 0.2, cable 100; Seeed A-02 37.4 x 17.5, 65; A-01 40 x 20, 80 | owner / TME, Seeed (A-02 in the S3 box is an assumption) |
| BME680 board 25.5 x 17.6 x 4.6 mm | | Adafruit page 5046 (BME688 STEMMA QT, drop-in); the 3660 page gives no mm; **module not final** |
| Walls 2.4 / end 2.0 / back 3.5 / lid 3.0 / baffle 2 + 3 + 2 / divider 2.0 | | owner: chamber walls >= 2 mm, antenna wall 1.5-2 mm |
| Louvres: slot 2.0, slat 1.8, 40 degrees (lid) / 50 degrees (bottom wall) | | owner: slots >= 1.5 mm, 45 degree rule |
| Cable-tie slots 2.8 x 1.6 mm, 13 mm either side of the opening centre | | for a 2.5 x 1.2 mm tie, **ASSUMED** |
| PETG data for the snaps | E 2550 MPa, 35 MPa, 5.2 % (Z) | Bambu Lab PETG Basic TDS V3.0 |
| Wall-screw sizes (head 7.2 / 8.0 mm) | | **ASSUMED** |

`py -3.12 scadparams.py --assumed` lists every `ASSUMED - verify` parameter: module heights, U.FL mated height, keep-out 10 mm (RF), `mod_inset`, coax bend radius, USB opening size, wall-screw sizes, BME PCB thickness, friction coefficient.

## 7. Pre-send checklist (`../../docs/ENCLOSURE_3D.md` section 2 item 8)

| Item | Status |
|---|---|
| Concept accepted | **not done - this is what the owner is asked for now** (section 9) |
| Assembly possible in the real place | **not verifiable** here; in the model: wall first, boards next, tie, lid last (section 3) |
| No supports in the given orientation | **done numerically** (`mesh_check`: 0 faces over 45 degrees; widest bridge 9.5 mm = tape cell, 8.0 mm = keyhole roof; text recess 4 mm; layer check of every STL: no feature thinner than 0.8 mm over 6 layers except the deliberate 55 degree louvre sample); not seen in Bambu Studio |
| No wall < 1.5 mm / orphan features | **done with exceptions**: thinnest measured 0.81 mm (lid, at the stepped text edges and the 45 degree lip tips), crush ribs and skins 1.0 mm; slicer layer preview **not done** |
| No collisions in the assembled model | **done** (envelope bodies); real board dimensions partly assumed |
| Watertight saved STL | **done** (0 open / non-manifold / reversed edges); Bambu Studio import **not done** |
| Fit samples included | **done** (6 STLs), **not printed** |
| Part <= ~240 mm | **done** (longest 78.8 mm) |
| Mating parts recomputed | **done** by construction (one `params.scad`, all STLs regenerated after the last change) |
| Print settings stated | **done** (section 5) |
| Snap-fit test strip with >= 3 variants | **provided** (`fit_sample_snap`), cycle test **not done** |

## 8. Verification actually performed (2026-11-27)

* `mesh_check.py` on all 8 STLs: PASS (base 3496 triangles / 40.9 cm3, lid 60 516 triangles / 16.1 cm3 because of the stepped text).
* `assembly_check.py` default: **64 / 64 passed** (also `--hdr 8.5`: 60 / 60, `--antenna-size A02` and `A01`: 56 / 56 without the air analysis). Highlights: outer size 78.78 x 69.54 x 30.50 mm equals the parameters; antenna distance 75.1 mm; nearest board metal 10.5 mm from a patch;
  the receptacle path from below is free and the opening widens from 14.0 to 16.7 mm at the outer face; the C6's USB-C meets a closed ceiling, the top face has 0 open probe points; tie slots outside the board outline; end arms 0.30 mm below the board edge;
  cables 32 / 37 mm of 100; wires clear of the divider; six hooks engaged (0.22 mm clearance), lid cannot lift; hook strain 0.56 %, clip strain 0.51 %; clips measured on the base alone;
  visible faces: front = outlet louvres and the name, top 0 openings, sides 0, bottom = louvres + opening + tie slots, back = release slots; text: about 940 mm2 of recess in 19 shapes spanning x 8.2..72.2 mm, z 10.6..47.0 mm, strokes narrower than 2 mm: 0.00 % of the floor, nearest louvre 4.0 mm, plate under the text 2.4 mm,
  lid solid in front of all four buttons.
* Air paths (0.5 mm voxels): the sensor zone is connected to the C6 channel only through the end gap (blocking the gap separates them); host column and sensor zone are separate volumes with the slots sealed and connected with the slots open; no top-face opening;
  16 blind pockets on the back face, 0 connected to the interior. Connectivity only - **no airflow, no temperature**.
* **Mutation checks** (`tests/unit/test_enclosure_meshes.py`): hole / flipped face / inverted shell / thin slab / 60 degree overhang / 30 mm bridge / 250 mm part fail the mesh checker; `--hdr 18` collides; a lid 0.4 mm too far out and one shifted 8 mm fail the hook checks;
  an expected USB opening or tie slots elsewhere make the visible-face probe report unexplained openings; the archived **rev02** housing (top notch, no bottom opening, no text) fails the R13 and R15 checks and the visible-face probe;
  a simulated pin hole in front of a button fails R16; demanding 30 mm louvre clearance or 4.5 mm strokes fails the text check; a wrong clip overhang fails the clip check.

**Not verified at all:** any print, any fit with real boards, strength / cycle life of the hooks and clips (calculations with typical datasheet values), friction coefficients, thermal behaviour, RF behaviour, airflow,
the real USB plug size and its retention, whether the engraved name reads well on the printed lid (the proof is a raster of the STL), the strength of keyholes and screw skins.

## 9. Decisions the owner must take to accept this concept

1. **The name:** `esp32-matter-gateway` ("gateway") - correct? Three lines acceptable?
2. **Layout A:** 78.8 x 69.5 x 30.5 mm (+4.2 mm in width against rev02), with about 42 mm of free air above the host and R2 only for the C6 - or prefer another trade-off (section 1)?
3. **Antenna keep-out 10.5 mm and distance 75.1 mm** (RF unmeasured) - or accept a smaller case with a smaller keep-out (`mod_inset`) and measure afterwards?
4. **Cable anchor by tie** (outside the case, tie cut to change the cable) instead of an inside clamp - acceptable?
5. **Foam-sealed divider slots** (assembly step 3) as the thermal barrier between host and sensor - acceptable, and who measures the temperature (section 1)?
6. **Mounting orientation:** vertical, sensor down, USB-C cable down - confirmed? (If the case lies flat, vents and opening must be redone.)
7. **Case off the wall to open** (hooks from the back) - still accepted?
8. Print the fit samples, do the cycle test, choose variants; measure the real boards (C6 buttons / U.FL / corners, BME680 corners and mounting holes, USB-C height and plug size); final BME680 module; antenna choice (BOM FPC or the S3 box antenna).
9. The lid has no hook at its top corners (no room beside the antenna zone); two hooks beside the divider and four at the bottom hold it. Accept, or add tape?

## References

- Owner's print checklist: `../../wytyczne_projektowania_druk3d (1).md`; owner's requirements R1-R17: `../../docs/ENCLOSURE_3D.md` section 3a
- Bambu Lab PETG Basic technical data sheet V3.0 (modulus, strength, elongation): <https://store.bblcdn.com/s1/default/cb94589bf7994fdcbfa833badefae9cd/Bambu_PETG_Basic_Technical_Data_Sheet.pdf>
- Seeed XIAO ESP32-S3 wiki (21 x 17.8 mm): <https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/>; XIAO ESP32-C6: <https://wiki.seeedstudio.com/xiao_esp32c6_getting_started/>
- Seeed's own KiCad design file of the S3 (U.FL, buttons, LED positions): <https://github.com/Seeed-Studio/OPL_Kicad_Library>
- Seeed FPC antennas A-02 / A-01: <https://www.seeedstudio.com/2-4GHz-FPC-Antenna-1-16dBi-for-XIAO-ESP32S3-p-6440.html>, <https://www.seeedstudio.com/FPC-Antenna-A-01-for-XIAO-ESP32C3-C5-p-6439.html>
- Adafruit BME688 STEMMA QT 25.5 x 17.6 x 4.6 mm: <https://www.adafruit.com/product/5046>; BME680 (3660): <https://www.adafruit.com/product/3660>
- Bosch BME680 datasheet: <https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme680/>
- Cantilever snap-fit formulas used (strain = 1.5 * delta * t / L^2, force = 3 E I delta / L^3, ramp friction F = P (mu + tan a) / (1 - mu tan a)): standard beam theory, e.g. Bayer/BASF snap-fit design guides
- OpenSCAD 2021.01: <https://openscad.org/documentation.html>; Bambu Lab H2D / Bambu Studio: <https://wiki.bambulab.com/>
