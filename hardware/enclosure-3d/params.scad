// =====================================================================================
// params.scad - THE ONLY PLACE WITH DIMENSIONS (enclosure rev03 CONCEPT DRAFT for the owner's acceptance, not test-printed)
//
// Read by OpenSCAD (enclosure.scad) AND by the Python tools (scadparams.py): keep every statement
// as  `name = <number | "string" | arithmetic of earlier names>;`  (no functions except min/max/abs/sqrt/trig,
// no ?:, several statements per line allowed).  Trigonometry is in DEGREES in both worlds.
//
// MOUNTING ORIENTATION (ASSUMED - the owner did not state it outright): the case hangs VERTICALLY on a wall or cabinet,
// BME680 sensor at the BOTTOM, the host's USB-C pointing DOWN through the bottom wall (rev03, R13).  Everything about dust (R3) and chimney airflow (R2) follows
// from this; if the case lies flat instead, the vents must be redone.
//
// Coordinate frame of the MOUNTED enclosure (looking at the front / lid):
//   X = long axis, Z = up, Y = out of the wall (Y = 0 is the back face that sits on the wall AND on the print plate),
//   the lid is at the largest Y.  Origin = outer left/bottom/back corner of the base.  The CAD frame is right-handed, so
//   seen from the FRONT, X runs from RIGHT to LEFT: X = 0 is the case end on the viewer's right.
//
// Source tags: [owner] owner's instruction  [seeed] Seeed public docs  [seeed-pcb] Seeed's own KiCad design file  [step] STEP file
//              [kicad] repo kicad_mod  [adafruit] Adafruit page  [print] owner's print checklist  [design] chosen here
//              [ASSUMED - verify] nothing in the repo or on the web confirms it
// =====================================================================================

rev = "rev03";                  // appended to every STL name

// ---------- print process constants ----------------------------------------------------
nozzle      = 0.4;              // [print]
layer_h     = 0.2;              // [print]
min_wall    = 1.6;              // [print] never design a printed wall thinner than this (>= 4 lines); checker hard limit is 0.8
max_bridge  = 10;               // [print] bridge limit
max_hole_h  = 8;                // [print] horizontal hole limit (diameter) without teardrop / 45 deg roof
louver_ang_lid  = 40;           // [design] lid is printed FLAT (wall normal = print Z): slot faces lean this far from the vertical, must be <= 45 [print]
louver_ang_wall = 50;           // [design] bottom wall prints STANDING (wall normal horizontal): slot faces are this far from the HORIZONTAL, must be >= 45 [print]

// ---------- joining the lid (R8) and holding the boards (R10): snap-fits only, NO screws anywhere in the case -----------------
// Material data for the snap calculation: Bambu Lab PETG Basic technical data sheet V3.0 (ISO 527): Young's modulus 2780 MPa (XY) / 2550 MPa (Z),
// tensile strength 51 MPa (XY) / 35 MPa (Z), elongation at break 9.5 % (XY) / 5.2 % (Z).  Typical values from Bambu's own tests, not guaranteed minima.
pet_E_z      = 2550;            // [bambu-tds] MPa, along the layer-stacking direction (the lid hooks are printed standing: their bending stress is ALONG Z)
pet_sig_z    = 35;              // [bambu-tds] MPa
pet_eb_z     = 5.2;             // [bambu-tds] % elongation at break, Z
snap_eps_max = 0.8;             // [design] allowed bending strain in the hook at full deflection, % (about 1/6 of the Z break elongation; stress E*eps = 20 MPa = 58 % of the Z strength). A design choice, NOT a tested limit
snap_b       = 4.5;             // [design] hook width (along the wall)
snap_t       = 1.8;             // [design] hook thickness in the deflection direction (>= 4 perimeters)
snap_h       = 1.0;             // [design] head protrusion (fit sample prints 0.8 / 1.0 / 1.2)
snap_q       = 1.0;             // [design] catch bump height on the case wall
snap_o       = 0.75;            // [design] engagement overlap at the default head protrusion
snap_t0      = snap_h + snap_q - snap_o;   // gap between the beam's inner face and the wall face (1.25)
snap_lead    = 30;              // [design] lead-in ramp angle from the insertion axis (easy closing); printable at any angle (faces up in print)
snap_ret     = 45;              // [print] return (catch) face angle from the axis: 45 deg is the steepest that prints without support (it faces down in print); a flat 90 deg catch would need support
snap_play    = 0.15;            // [design] play between head catch face and bump underside (lid can rattle by this much along Y)
snap_flat    = 1.2;             // [design] flat tip of the head
snap_yb      = 3.9;             // [design] bump underside start above the back plate's inner face
snap_slot_skin = 1.0;           // [design] release slots are blind pockets from the back with this skin (pierce with a screwdriver blade); closed = no air path until used
snap_mu      = 0.3;             // [ASSUMED - verify] friction coefficient PETG on PETG for the force estimate (no measurement)

// ---------- rounded shape (R9) --------------------------------------------------------------------------------------
corner_r  = 5.0;                // [owner R9] outer radius of the four edges parallel to Y (they stand vertically in print)
corner_ri = 2.4;                // [design] inner radius of the cavity corners (wall at the corner stays >= 1.9 mm: concentric with the outer arc)
ch_back   = 0.6;                // [design] 45-degree chamfer on the back edge (also relieves elephant foot on the print plate)
ch_lid    = 1.6;                // [design] 45-degree chamfer on the lid's outer edge (printed on the plate side: grows outwards at 45 degrees)

// ---------- wall thicknesses -------------------------------------------------------------
t_wall = 2.4;                   // [design] top / bottom wall
t_end  = 2.0;                   // [owner] antenna walls ~1.5-2 mm (end walls carry the antennas)
t_back = 3.5;                   // [design] back plate (countersink for the wall screws + skin)
t_lid  = 3.0;                   // [design] lid plate (countersink 1.45 deep leaves 1.55)


// ---------- XIAO modules (S3 / S3 Plus / C6, same outline) ------------------------------------
xiao_w       = 17.78;           // [step] bare-PCB STEP of the XIAO ESP32-S3 (old project, circuit_ESP32C3_Xiao/lib/XIAO-ESP32S3.step): 17.78 mm; [seeed] wiki "21 x 17.8 mm"; the C6 outline is assumed identical (footprints agree)
xiao_l       = 21.14;           // [step] 21.135 mm in the same STEP (the S3 footprint says 20.95, the C6 footprint 21.0; the STEP is the largest, so it is the safe pocket size)
xiao_l_extra = 0.0;             // [ASSUMED - verify] extra pocket length below the board; Seeed lists the S3 Plus as 21 x 17.8 mm (same outline, the extra pads sit on the long edges) so 0; set 2-3 if a measured Plus is longer
xiao_pcb_t   = 1.6;             // [seeed-pcb] `(general (thickness 1.6))` in Seeed's own ESP32S3.kicad_pcb (the STEP exported from it shows 1.51 for the board body without mask/copper). A design value, not a caliper measurement - verify on a real board; the C6 is assumed the same
xiao_top_h   = 3.3;             // [ASSUMED - verify] tallest part above the PCB front face (USB-C receptacle ~3.2)
usb_w        = 9.0;             // [kicad] receptacle width (+-4.5 at the board edge)
usb_h        = 3.2;             // [ASSUMED - verify] receptacle height
usb_over     = 1.5;             // [kicad] receptacle sticks out 1.5 mm beyond the board edge (y = -12.0 vs -10.5)
// Positions below are for the XIAO ESP32-S3, read from Seeed's own design file (github.com/Seeed-Studio/OPL_Kicad_Library,
// "Seeed Studio XIAO ESP32S3/ESP32S3.kicad_pcb", footprints ANT1, K1, K2, D3). View: component side, USB-C at the top;
// u = from the viewer-left board edge, v / dv = from the lower / USB end edge. The XIAO ESP32-C6 has NO design file in that repo:
// its values are ASSUMED equal to the S3's - verify on a real board (the C6 button order may differ).
xiao_ufl_u   = 4.54;            // [seeed-pcb] U.FL ANT1 body centre (pads span x 3.20..5.88 from the left edge); S3 only
xiao_ufl_v   = 1.73;            // [seeed-pcb] ... from the lower board edge (pads reach the edge)
xiao_ufl_s   = 2.6;             // [seeed-pcb] footprint name U-FL3P-SMD-2.6X2.6X1.0MM
xiao_ufl_h   = 1.0;             // [seeed-pcb] ... socket height 1.0 mm (from the footprint name)
ufl_mated_h  = 2.5;             // [ASSUMED - verify] mated U.FL plug height above the PCB
btn_boot_u   = 14.73;           // [seeed-pcb] BOOT = K2 (net GPIO0) is on the viewer-RIGHT; centre 5.84 right of the board centre
btn_rst_u    = 3.05;            // [seeed-pcb] RESET = K1 (net EN) is on the viewer-LEFT; centre 5.84 left of the board centre
btn_dv       = 1.65;            // [seeed-pcb] both buttons: centre 1.65 mm from the USB end edge (pads reach 0.1 mm from it)
led_u        = 14.78;           // [seeed-pcb] yellow user LED D3 (net IO21/USER_LED), 5.89 right of the board centre
led_dv       = 3.86;            // [seeed-pcb] ... 3.86 mm from the USB end edge (the red charge LED CHG0 mirrors it on the left)
hdr_h        = 0.0;             // [design] pin-header body+pins below the PCB back (0 = soldered wires; 8.5 = 2.54 mm headers). Posts are 15 high so both fit
hdr_rows_w   = 2.5;             // [design] header row width (2.54 pitch)

// ---------- antennas (all glued INSIDE; both modules get an external antenna - owner 2026-11-27) -------------
// Candidate patches (flat zone must be >= 45 x 22 so that all fit):
//   BOM  2J 2JF0802P-010MC137-UFL : 39.6 x  8.4 x 0.2 mm, cable 100 mm   [owner/TME]
//   Seeed FPC antenna A-02 (S3)   : 37.4 x 17.5      mm, cable  65 mm   [seeed] (assumed to be the one in the S3 box - not confirmed)
//   Seeed FPC antenna A-01 (C3/C5): 40.0 x 20.0 x 0.2 mm, cable  80 mm   [seeed]
ant_len    = 39.6;              // [owner/TME] chosen patch length (default: BOM antenna); edit these three lines for A-02 / A-01
ant_w      = 8.4;               // [owner/TME] chosen patch width
ant_cable  = 100;               // [owner/TME] chosen cable length (mm); assembly_check --antenna-size A02|A01 re-checks the cable paths
ant_t      = 0.2;               // [owner/TME]
ant_flat_w = 22;                // [owner] smooth rib-free zone on the end wall: width (along Y) ...
ant_flat_l = 45;                //         ... and length (along Z) - covers all three candidates
ant_seat_m = 0.4;               // [design] seat margin around the patch
ant_seat_d = 0.3;               // [design] seat depth (45-deg chamfered edges), wall stays 2.0 - 0.3 = 1.7
ant_keep_m = 10;                // [ASSUMED - verify] no metal (PCB, nut, screw) within ~10 mm of a patch (owner "no metal near"; the 10 is a rule of thumb, no RF measurement)
coax_min_bend = 7;              // [ASSUMED - verify] min bend radius of the 1.37 mm coax (~5 x OD)
wire_min_bend = 4;              // [design] AWG28 hook-up wire

// ---------- BME680 board (Adafruit BME680 breakout is the candidate; NOT final) ---------------
bme_w     = 25.5;               // [adafruit] product 5046 (BME688 STEMMA QT, drop-in replacement) page: 25.5 x 17.6 x 4.6 mm; the 3660 page gives no mm; some retailers list 18 x 16.5 x 2.8 for 3660 (smaller: fits inside this envelope)
bme_h     = 17.6;               // [adafruit] see above
bme_pcb_t = 1.6;                // [ASSUMED - verify]
bme_top_h = 3.0;                // [adafruit] 4.6 total - 1.6 PCB (assumed split)

// ---------- widths: two columns (rev03 layout A) - host column (host bottom, USB down) | divider | sensor + C6 column -------------
min_ant_sep = 60;               // [owner] antenna centre distance must stay >= 60 mm
mod_inset   = 10.5;             // [ASSUMED - verify] board edge to the antenna wall = the keep-out (ant_keep_m), rule of thumb, RF unmeasured
mid_h       = 7.0;              // [design] divider centre to the host's inner edge: divider 1.0 + clip arm 1.9 + hook zone
bme_gap     = 3.5;              // [design] divider centre to the BME board edge: divider 1.0 + clip arm 1.9 + 0.6
h_col       = mod_inset + xiao_w + mid_h;                               // host-side wall inner face -> divider centre
c_col       = max(mid_h + xiao_w + mod_inset, bme_gap + bme_w + mod_inset);   // divider centre -> sensor/C6-side wall inner face (the 25.5 mm BME board sets it)
Win         = max(min_ant_sep + 1, h_col + c_col);                      // inner length = antenna centre distance
ant_sep     = Win;
Lo          = Win + 2*t_end;    // outer length
Din         = 24;               // [design] inner depth: the flat antenna zone is 22 wide (+ 1 mm each side)
Hbase_y     = t_back + Din;     // depth of the base (front edge of the walls)
Do          = Hbase_y + t_lid;  // total depth with the lid

// ---------- vertical stack (bottom -> top): bottom wall | sensor zone | baffle | module zone | top wall ----------
bme_post  = 6.0;                // [design] standoff under the sensor board (air + wiring behind it)
bme_below = 5.0;                // [design] air space between the bottom wall and the board (inlet side)
bme_above = 6.0;                // [design] air space between the board and the baffle
Hs        = bme_below + bme_h + bme_above;          // sensor zone inner height
part_wall = 2.0;                // [design] each of the two baffle walls
part_gap  = 3.0;                // [design] closed air gap between them (no shared solid plate; closed by the lid, the back plate and end caps)
part_t    = 2*part_wall + part_gap;
mod_bottom = 6.0;               // [design] free height under the boards: U.FL cable loop, wire bend, air entering the channels
mod_top_gap = 2.0;              // [design] C6 top edge below the ceiling: its (unused) USB-C receptacle sticks out 1.5 mm and stays 0.5 mm clear of the ceiling
Hu        = mod_bottom + xiao_l + xiao_l_extra + mod_top_gap;   // C6 zone inner height (C column)
z_s0      = t_wall;             // inner bottom (floor of the sensor zone)
z_p0      = z_s0 + Hs;          // underside of the baffle
z_p1      = z_p0 + part_t;      // top side of the baffle = floor of the module zone
z_u1      = z_p1 + Hu;          // inner ceiling
Ho        = z_u1 + t_wall;      // outer height
ant_z1    = z_u1 - corner_ri - 0.3 - (ant_flat_l - ant_len)/2; ant_z0 = ant_z1 - ant_len;     // patch centred in the 45 mm flat zone, whose top stops 0.3 mm below the inner corner radius (feed end = lower end)
ant_y     = t_back + Din/2;     // patch centre line (depth)
g_gap     = 7.0;                // [design] air gap between each end wall and the baffle end: the chimney passes here, the end-wall flat zone stays free of ribs

// ---------- module placement ---------------------------------------------------------------------------------
lid_gap      = 4.0;             // [design] air between the tallest part and the lid (= how far a board can lift); also keeps wall above the USB notch
clr          = 0.30;            // [design] clearance board edge -> guide arm (default = middle variant of the fit sample, which prints 0.15 / 0.30 / 0.45)
guide_t      = 1.6;             // [print] thickness of corner guide arms
sup_x        = 3.0;             // [design] corner support under the board, along the width (pads start 2.35 from the end, so z stays below that)
sup_z        = 1.5;             // (header rows span +-8.9 around the board centre, supports start at +-9.0)
arm_z        = 1.5;             // [design] arm length along the side edge: ends 9.0 mm from the board centre, clear of 2.54 mm header rows (+-8.89) and of the castellated pads
end_arm      = 4.0;             // [design] arm length along the lower end edge
h_post       = Din - lid_gap - xiao_top_h - xiao_pcb_t;   // standoff height under the boards (15.1): air + wires behind the boards
ym_b         = t_back + h_post;                        // board back plane
ym_f         = ym_b + xiao_pcb_t;                      // board front plane
ym_top       = ym_f + xiao_top_h;                      // highest component
host_bot_gap = usb_over + 0.5;  // [design] host board USB-end edge above the bottom wall's inner face: the receptacle front then sits 0.5 mm above it
// X positions: host S3 in the viewer's RIGHT column (small X), C6 and BME680 in the viewer's LEFT column (large X).  Seen from the front X runs
// right to left.  The host stands UPSIDE DOWN (USB-C end down, 180 degrees in the plane, component side to the lid): its U.FL is then near the
// small-X wall, its pad row 8-14 (3V3, GND, 5V at the USB end) faces the divider.  The C6 stands USB-C up (no opening needed), U.FL near the large-X wall.
x_div = t_end + h_col;                                    // vertical divider between the two columns
xh0   = t_end + mod_inset;      xh1 = xh0 + xiao_w;       // host board edges
xc1   = Lo - t_end - mod_inset; xc0 = xc1 - xiao_w;       // C6 board edges (xc1 = viewer-left edge, u = 0, standard orientation)
zh0   = z_s0 + host_bot_gap;                              // host lower edge (USB-C end)
zh1   = zh0 + xiao_l + xiao_l_extra;                      // host upper edge (U.FL end)
zc0   = z_p1 + mod_bottom;                                // C6 lower edge (U.FL end)
zc1   = zc0 + xiao_l + xiao_l_extra;                      // C6 upper edge (USB-C end, unused)
div_t = 2.0;                    // [design] divider thickness (chamber walls >= 2 mm)
div_slot_w = 12;                // [design] wire slot through the divider (Z size at the base, 45-degree roof, flat top 6 mm)
div_slot_h = 6;                 // [design] ... Y size
div_s1_z  = z_s0 + 12.5;        // [design] slot 1 (BME wires 3V3/GND/SDA/SCL, sensor -> host's 3V3/GND pads at the USB end): centre height
div_s2_z  = zc0 + 8.0;          // [design] slot 2 (host <-> C6: UART, RTS/CTS, EN, BOOT, 5 V, GND): centre height, near the C6's lower pads

// ---------- the ONE USB-C opening (R13): host, in the BOTTOM wall, facing down; no other USB opening, no plug (rev03) ---------
usb_open_w = 14.0;              // [ASSUMED - verify] clear width for a plug overmould up to ~12.4 x 6.5 mm (standard USB-C plug: ~12 x 6.5 typ.)
usb_open_h = 8.0;               // [ASSUMED - verify] clear depth (Y) centred on the receptacle; the opening is a slot in the bottom wall, open towards the lid side (print top, no bridge)
usb_lead   = 1.5;               // [design] 45-degree lead-in bevel around the opening on the outer face (cable bends smoothly, no sharp edge)
tie_x      = 13.0;              // [design] cable-tie slots beside the opening: distance from the opening centre (outside the board outline)
tie_w      = 2.8;               // [design] slot width (fits a 2.5 mm cable tie)
tie_h      = 1.6;               // [design] slot height (fits a 1.2 mm tie)
led_on    = 0;                  // [owner] light window for the on-board LED: OFF (no BOOT/RESET holes any more, R16; the LED window stays a parameter for later)
led_d     = 2.0;                // [design]

// ---------- engraved device name (R15), on the outer face of the lid -----------------------------------------------------
name_l1   = "esp32-";           // [owner R15] "esp32-matter-gateway" in three lines (the owner typed "gatway": "gateway" is assumed, CONFIRM before printing)
name_l2   = "matter-";
name_l3   = "gateway";
name_font = "Bahnschrift:style=Bold";   // [design] Windows system font (variable font); chosen because its "e" keeps an open aperture after the 0.8 mm closing (Liberation Sans Bold: the e turned into an o). NOT bundled: building on another machine needs this font or the text changes
name_size = 10.0;               // [design] OpenSCAD text size (cap height about 0.72 of it)
name_spacing = 1.2;            // [design] letter spacing factor of text() (1 = font default); > 1 keeps the recessed letters apart after the stepped outline has grown
name_emb  = 0.0;                // [design] outline shift per side (negative = lighter than the raw glyph): the widest layer (outer face = the visible shape) is emb+0.5; above ~0.4 the aperture of the "e" and the counters of 3, 2 close up (checked on renders); strokes at the recess floor still >= 2 mm (checked on the lid STL)
name_close = 0.45;             // [design] closing radius of the name outline: material gaps narrower than 2*name_close (0.90 mm) are filled, so no printed wall stays below the 0.8 mm minimum (0.40 left a 0.80 mm spot that mesh_check rejects; 0.43 produced a degenerate sliver in the mesh)
name_depth = 0.6;               // [design] recess depth (3 layers); plate stays 3.0 - 0.6 = 2.4 mm
name_pitch = 12.0;              // [design] line pitch (mm)
name_zc   = 29.0;               // [design] height of the middle line's centre (clear of the louvres by >= 3 mm, checked)
name_louvre_gap = 3.0;      // [owner R15] the text keeps >= 3 mm from every louvre opening (checked on the lid STL)
name_stroke_min = 2.0;      // [design] strokes at the recess floor >= 2 mm (the recess is a bridge in print; checked on the lid STL)

// ---------- BME680 placement (sensor zone, bottom of the C column) ------------------------------------------------
bme_x1    = Lo - t_end - mod_inset;       // BME board outer edge keeps the same keep-out to the antenna wall as the C6
bme_x0    = bme_x1 - bme_w;
bme_z0    = z_s0 + bme_below;
bme_z1    = bme_z0 + bme_h;
bme_yb    = t_back + bme_post;  // board back plane

key_x       = 14.0;             // [design] x of the lower keyhole chamber from the host-side wall inner face (wall-screw head edge >= 10 mm from the patch)

// ---------- wall mounting (R4): keyholes (sealed chambers), screws from the back, tape recess ----------------
keyholes_on = 1;                // [owner] two keyholes ("great idea"), each in its own SEALED chamber behind the plate: no air path into the case
key_head_d  = 7.6;              // [ASSUMED - verify] head hole for a wall screw with a head of at most 7.2 mm (e.g. 3.5-4 mm pan head); a larger head would break the 10 mm keep-out to the antenna patch
key_slot_w  = 4.4;
key_slot_l  = 5.0;
key_head_t  = 3.5;              // [ASSUMED - verify] screw head thickness
key_cav_m   = 0.2;              // [design] cavity wall clearance around the head hole
key_cav_h   = key_head_t + 0.5; // cavity height above the plate
key_ring_t  = 1.6;              // [design] chamber wall and roof thickness
key_roof_t  = 1.6;
key_dx      = 36.0;                                        // [owner R17] distance between the two wall-screw axes (round number: easy to mark and drill; printed on the back)
key_zb      = zh1 + 14.0;                                  // [owner R17] BOTH chambers on ONE horizontal line: outer lower edge 14 mm above the host
key_zb2     = key_zb;                                      // second chamber: same height (R17), mirrored about the centre line
key_zh      = key_zb + key_ring_t + (key_head_d + 2*key_cav_m)/2;   // head-hole centre height of the lower chamber
key_zh2     = key_zb2 + key_ring_t + (key_head_d + 2*key_cav_m)/2;  // ... of the upper chamber (the case hangs on this one, slot upwards)
key_xc      = Lo/2 - key_dx/2;                             // left chamber (seen from the back), behind the host column
key_xc2     = Lo/2 + key_dx/2;                             // right chamber, behind the C6 column: symmetric about the case centre line
sh_on       = 1;                // [owner] countersunk screw holes from the back (screwed into the wall from inside the case, boards not yet fitted)
sh_d        = 4.3;              // [ASSUMED - verify] 4 mm screw
sh_head_d   = 8.0;              // [ASSUMED - verify] countersunk head
sh_skin     = 1.0;              // [design] closed skin at the back face (5 layers; the owner's rule: never below 0.8): no air path until the screw or a drill pierces it
sh_x        = xh0 + xiao_w/2;   // [design] screw hole 1: behind the host column, between the two keyholes (x of the host centre)
sh_z        = 17.0;             // [design] ... height (clear of the drilling marks of R17 and of the board posts)
sh_x2       = xc0 + xiao_w/2;   // [design] screw hole 2: behind the C6 (x of the C6 centre, in the rear gap)
sh_z2       = zc1 - 5.0;       // [design] moved up from the C6 mid-height: the upper keyhole chamber (key_xc2) now sits behind the C6 column below it
sh_half     = 44;               // [design] countersink half angle (< 45)
tape_on     = 1;                // [owner] shallow recess on the back for double-sided tape
tape_w      = 9.5;              // [design] cell width: a recess is a bridge in print, so cells are <= 10 mm wide with a 3.5 mm rib between them
tape_rib    = 3.5;
tape_n      = 2;
tape_d      = 0.5;              // [design] recess depth
tape_m      = 6;                // [design] margin to the bottom edge
tape_xc     = Lo/2;             // [design] x of the middle of the two tape cells (between the keyhole chambers and the C6's screw hole)
tape_z1     = 30;               // [design] upper end of the tape cells: stays below the drilling marks of R17 (dimension line z = dim_z)

// ---------- drilling marks on the back (R17): dimension line + extension lines + the distance as recessed text, between the keyholes ----------
dim_on      = 1;
dim_txt     = "36 mm";          // [owner R17] must equal key_dx (checked by a test)
dim_depth   = 0.4;              // [design] recess depth on the back face (2 layers; the back face is the print bed side, so the lines are open bridges 1 mm wide)
dim_w       = 1.0;              // [design] line width (>= 0.8 print minimum)
dim_z       = 33.5;             // [design] height of the dimension line
dim_ext_z1  = dim_z - 1.0;      // [design] extension lines (down from the holes) start below the dimension line
dim_ext_z2  = key_zh - key_head_d/2 - 1.0;   // ... and end 1 mm below the head hole of the keyhole
dim_txt_size = 6.0;             // [design] OpenSCAD text size: strokes of the bold face stay >= 1 mm
dim_txt_z   = dim_z + 2.0;      // [design] text baseline: above the dimension line, between the extension lines


// ---------- ventilation (R2/R3): inlets down / sideways, outlets sideways (louvres angled down), no slots in upward faces ----------
louver_slot = 2.0;              // [print] slot width measured perpendicular to the louvre (>= 1.5)
louver_slat = 1.8;              // [print] slat thickness (>= 1.5)
lid_pitch_u    = (louver_slot + louver_slat)/cos(louver_ang_lid);     // slot pitch along the lid (mm)
wall_pitch_u   = (louver_slot + louver_slat)/cos(louver_ang_wall);    // slot pitch along the bottom wall (mm)
// inlets (sensor zone): bottom wall (faces down) + low lid louvres (face sideways/down)
s_len     = 24;                 // length of the sensor-zone groups along X
v_bot_n   = 4;    v_bot_y = t_back + 1;
v_slow_n  = 2;    v_slow_z = z_s0 + 2;
// outlets (module zone): two lid groups, one per channel; louvre outer opening is LOWER than the inner one
v_out_len = 16;   v_out_n = 2;
v_out_zt  = z_u1 - 7;           // top edge of the outlet groups (the BOOT/RESET pin holes sit above, at z_u1 - 3.65)

// ---------- label recess in the lid (outer face, sensor zone) ----------------------------------------------
label_x = Lo/2;
label_z = z_s0 + 20.5;

// ---------- board clips (R10): the four side guide arms of every board are flexible cantilevers with a small lip over the board corner --------
clip_ov    = 0.7;               // [design] lip overhang over the PCB corner (fit sample 0.5 / 0.7 / 0.9 together with clr 0.15 / 0.30 / 0.45)
clip_play  = 0.10;              // [design] gap between the lip underside and the PCB front face: no pressure at rest (nothing presses on the RF/U.FL area, USB-C shell or buttons), the board can lift by this much only
clip_flat  = 1.2;               // [design] flat tip of the lip
clip_lead  = 30;                // [design] lead-in ramp angle (board is pressed in from the front)
clip_ret   = 45;                // [print] underside (retention) angle: 45 deg is the steepest that prints without support
clip_eps_max = 0.8;             // [design] allowed bending strain (%) of the arm at insertion, see snap_eps_max
clip_keep_ufl = 0.5;            // [design] lip stays >= 0.5 mm clear of the U.FL pad area, the buttons and the USB-C receptacle (footprints from Seeed's S3 design file)

// ---------- snap hook positions (lid hooks, case bumps, back-plate release slots) -----------------------------------------
snap_zm      = z_u1 - 7.6;      // [design] z of the two hooks beside the divider (above the wire slot z 45..58, below the ceiling)
snap_zb1     = z_s0 + 4.1;      // [design] z of the lower hook pair at each end wall (below the antenna flat zone)
snap_zb2     = z_s0 + 10.1;     // [design] z of the upper hook pair at each end wall
snap_seam    = 0.6;             // [design] 45-degree chamfers on both sides of the lid / case parting line = a deliberate even V-groove (R10: the only visible seam)

// ---------- fit samples (coupons) ----------------------------------------------------------
fs_clr1 = 0.15;  fs_clr2 = 0.30;  fs_clr3 = 0.45;           // module guide clearances
fs_usb1 = 13.0;  fs_usb2 = 14.0;  fs_usb3 = 15.0;           // USB notch widths
fs_emb1 = -0.10; fs_emb2 = 0.00;  fs_emb3 = 0.10;           // engraved-name embolden per side (stroke width at the recess floor)
fs_ov1 = 0.5;    fs_ov2 = 0.7;    fs_ov3 = 0.9;              // board clip lip overhang (paired with fs_clr1..3)
fs_h1 = 0.8;     fs_h2 = 1.0;     fs_h3 = 1.2;               // lid hook head protrusion (overlap with the case bump 0.55 / 0.75 / 0.95)
fs_seat1 = 0.2;  fs_seat2 = 0.3;  fs_seat3 = 0.4;           // antenna seat depths
fs_ang1 = 45;    fs_ang2 = 50;    fs_ang3 = 55;             // louvre angle test (standing wall, angle from the wall normal)
fs_tape1 = 6.5;  fs_tape2 = 8.0;  fs_tape3 = 9.5;           // tape recess cell widths (all <= 10 mm bridge; 9.5 is the default)
