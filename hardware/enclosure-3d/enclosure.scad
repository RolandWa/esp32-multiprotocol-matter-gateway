// =====================================================================================
// Gateway enclosure rev03 CONCEPT DRAFT (for the owner's acceptance) - not test-printed.  All numbers live in params.scad.
//
//   openscad -D 'part="base"' -o out.stl enclosure.scad
//   part = "base" | "lid" | "fit_modules" | "fit_antenna" | "fit_snap" | "fit_louvre" | "fit_mount" | "fit_name"
//
// NO SCREWS close the case or hold a board (owner R8/R10): the lid has 6 cantilever hooks that click behind wedge bumps on
// the divider and the end walls; every board sits on 4 corner supports and is clipped by 4 flexible arms with a small lip.
// Everything that snaps is INSIDE the case; the hooks are released from the BACK through blind slots in the back plate.
// Assumed mounting: vertical, BME680 at the bottom, the HOST stands upside down (USB-C end down) so that its USB-C points through the bottom wall.
//
// Print orientation (FIXED by the STL, do not rotate in the slicer):
//   base : back face (wall side) on the plate, open front up;            print z = mounted Y,  print y = Ho - Z
//   lid  : OUTER face on the plate, hooks stand up from the inner face;   print z = Do - Y,     print y = Z
// =====================================================================================
include <params.scad>;

part = "base";
$fn = 40;
eps = 0.01;

// ---------------------------------------------------------------- helpers
module rbox(xa, xb, ya, yb, za, zb) {
    translate([min(xa,xb), min(ya,yb), min(za,zb)])
        cube([abs(xb-xa), abs(yb-ya), abs(zb-za)]);
}
module cyl_y(x, z, y0, h, d, fn=40) {            // cylinder along +Y starting at y0
    translate([x, y0, z]) rotate([-90,0,0]) cylinder(d=d, h=h, $fn=fn);
}
function span_u(n, ang) = (n*(louver_slot+louver_slat) - louver_slat)/cos(ang);

// Tilted slots through a wall.  O = point on the INNER face (middle of the group along its length,
// first slot starts at u = 0), U = direction in which the slots are stacked, V = outward normal,
// t = wall thickness.  The slot centre line moves by -tan(ang) in u per mm of v, i.e. the OUTER opening lies at
// smaller u: with U = +Z (lid) the outer opening is LOWER (faces down), with U = +Y on the bottom wall it faces the wall.
module louver(O, U, V, len, n, t, ang) {
    tn  = tan(ang);
    su  = louver_slot/cos(ang);
    pu  = (louver_slot + louver_slat)/cos(ang);
    ext = 0.6;
    L   = cross(U, V);
    multmatrix([[U[0],V[0],L[0],O[0]],
                [U[1],V[1],L[1],O[1]],
                [U[2],V[2],L[2],O[2]],
                [0,0,0,1]])
        translate([0,0,-len/2])
            linear_extrude(height=len)
                for (k=[0:n-1])
                    polygon([[k*pu + ext*tn,           -ext],
                             [k*pu - (t+ext)*tn,        t+ext],
                             [k*pu - (t+ext)*tn + su,   t+ext],
                             [k*pu + ext*tn + su,      -ext]]);
}

// USB-C notch through the top wall: open towards the front (= print top), no roof/bridge; the lid closes it.
module usb_notch(xc, w, y_low, y_top, z0, len) {
    rbox(xc - w/2, xc + w/2, y_low, y_top, z0, z0 + len);
}
// smooth lead-in of the bottom opening: 45-degree bevels on the outer face (sides and the lower-y edge); no overhang, the bottom wall stands in print
module usb_leadin(xc, w, y_low, y_top, c) {
    translate([0, y_low - c, 0]) rotate([-90,0,0]) linear_extrude(height = y_top - y_low + c)      // sides: trapezoid in (x, z), extruded along +Y
        polygon([[xc - w/2 - c, 0.0], [xc + w/2 + c, 0.0], [xc + w/2, -c], [xc - w/2, -c]]);
    translate([xc - w/2 - c, 0, 0]) rotate([90,0,90]) linear_extrude(height = w + 2*c)               // y_low edge: trapezoid in (y, z), extruded along +X
        polygon([[y_low - c, 0.0], [y_low + eps, c], [y_low + eps, -c], [y_low - c, -c]]);
}
// cable-tie slots beside the opening (tie head inside the case, loop around the cable outside = anchor against a tug)
module tie_slots(xc, yc) {
    for (sx = [-1, 1]) rbox(xc + sx*tie_x - tie_w/2, xc + sx*tie_x + tie_w/2, yc - tie_h/2, yc + tie_h/2, -1, z_s0 + 0.01);
}

// ---------------------------------------------------------------- rounded outer shape (R9)
// rounded rectangle in the XZ plane (corner radius corner_r), shrunk by `ins` (centres stay, radius shrinks)
module rr2d(ins) {
    hull() for (cx=[corner_r, Lo-corner_r], cz=[corner_r, Ho-corner_r])
        translate([cx, cz]) circle(r=corner_r-ins, $fn=48);
}
module slab(ya, yb, ins) {                       // rounded-rectangle prism between Y = ya and yb
    translate([0, yb, 0]) rotate([90,0,0]) linear_extrude(height=yb-ya) rr2d(ins);
}
// outer body between y0 and y1 with 45-degree chamfers c0 (at y0) and c1 (at y1)
module outer_solid(y0, y1, c0, c1) {
    hull() { slab(y0, y0+eps, c0); slab(y0+c0, y1-c1, 0); slab(y1-eps, y1, c1); }
}
module cavity() {                                // inner volume, open to the front, inner corner radius corner_ri
    translate([0, Hbase_y+1, 0]) rotate([90,0,0]) linear_extrude(height=Hbase_y+1-t_back)
        hull() for (cx=[t_end+corner_ri, Lo-t_end-corner_ri], cz=[z_s0+corner_ri, Ho-t_wall-corner_ri])
            translate([cx, cz]) circle(r=corner_ri, $fn=32);
}

// ---------------------------------------------------------------- board cradle: 4 corner supports + 4 flexible clip arms (R10)
// Side arms are cantilevers (root at the back plate) with a small lip over the PCB corner: 45-degree underside (prints without
// support), lead-in ramp on top.  `thk` = PCB thickness; the lip underside sits clip_play above the PCB front face.
module clip_lip(cx, dx, cz, dz, c, ov, yl) {
    u1 = c + ov;                                                    // lip reaches this far from the arm's inner face towards the board
    x0 = cx - dx*c;                                                 // arm inner face
    za = cz - dz*(c + guide_t);  zb = cz + dz*arm_z;
    translate([0, 0, min(za, zb)]) linear_extrude(height=abs(zb - za))
        polygon([[x0 - dx*0.2, yl + u1/tan(clip_ret)], [x0, yl + u1/tan(clip_ret)], [x0 + dx*u1, yl], [x0 + dx*u1, yl + clip_flat],
                 [x0, yl + clip_flat + u1/tan(clip_lead)], [x0 - dx*0.2, yl + clip_flat + u1/tan(clip_lead)]]);   // 0.2 mm root inside the arm: robust union
}
module cradle(bx0, bx1, bz0, bz1, yb0, y_b, thk, c, ov) {
    g  = guide_t;
    yl = y_b + thk + clip_play;                                     // lip underside
    yt = yl + clip_flat + (c + ov)/tan(clip_lead) + 0.3;            // top of the arms
    for (sx=[0,1], sz=[0,1]) {
        cx = (sx==0) ? bx0 : bx1;   dx = (sx==0) ? 1 : -1;
        cz = (sz==0) ? bz0 : bz1;   dz = (sz==0) ? 1 : -1;
        rbox(cx, cx+dx*sup_x, yb0-eps, y_b, cz, cz+dz*sup_z);                           // support under the corner
        rbox(cx-dx*c, cx-dx*(c+g), yb0-eps, yt, cz-dz*(c+g), cz+dz*arm_z);              // flexible arm along the side edge
        clip_lip(cx, dx, cz, dz, c, ov, yl);
        if (sz==0)
            rbox(cx-dx*(c+g), cx+dx*end_arm, yb0-eps, yl-0.3, cz-c, cz-c-g);            // fixed arm along the lower end edge (top kept below the lip tip: no edge contact)
    }
}

// ---------------------------------------------------------------- lid snap hooks (R8)
// Hook geometry in the (t, y) plane: t = distance from the wall face (divider or end wall) towards the beam, y = depth.
function hk_ye(h, t0) = t_back + snap_yb - snap_play + t0 - h - h/tan(snap_lead) - snap_flat;   // y of the beam end (lowest point)
// beam + head, world coordinates, wall face at x = xf, s = +1 beam on the +x side of the face, -1 on the -x side
module snap_hook(xf, s, z0, h=snap_h, t0=snap_t0) {
    ye = hk_ye(h, t0);
    pts = [[0, 0], [-h, h/tan(snap_lead)], [-h, h/tan(snap_lead) + snap_flat], [0, h/tan(snap_lead) + snap_flat + h/tan(snap_ret)],
           [0, Hbase_y + 1 - ye], [snap_t, Hbase_y + 1 - ye], [snap_t, 0]];
    translate([0, ye, z0]) linear_extrude(height=snap_b)
        polygon([for (p = pts) [xf + s*(t0 + p[0]), p[1]]]);
}
// catch bump on the wall (case side): underside 45 degrees (prints), top ramp snap_lead
module snap_bump(xf, s, z0, q=snap_q) {
    yb0 = t_back + snap_yb;
    pts = [[-0.3, 0], [0, 0], [q, q/tan(snap_ret)], [q, q/tan(snap_ret) + snap_flat], [0, q/tan(snap_ret) + snap_flat + q/tan(snap_lead)], [-0.3, q/tan(snap_ret) + snap_flat + q/tan(snap_lead)]];   // 0.3 mm root inside the wall: robust union
    translate([0, yb0, z0 - 0.5]) linear_extrude(height=snap_b + 1.0)
        polygon([for (p = pts) [xf + s*p[0], p[1]]]);
}
// release slot in the back plate under the hook tip: blind pocket from the back, skin snap_slot_skin towards the inside
module snap_slot(xf, s, z0, h=snap_h, t0=snap_t0) {
    ta = t0 - h - 0.4;  tb = t0 + 1.2;
    rbox(xf + s*ta, xf + s*tb, -1, t_back - snap_slot_skin, z0 + 0.3, z0 + snap_b - 0.3);
}
// the six hook stations: [x of the wall face, side, z]
hooks = [[x_div + div_t/2, 1, snap_zm], [x_div - div_t/2, -1, snap_zm],
         [t_end, 1, snap_zb1], [t_end, 1, snap_zb2],
         [Lo - t_end, -1, snap_zb1], [Lo - t_end, -1, snap_zb2]];

// ---------------------------------------------------------------- baffle of the sensor column (double wall, one end gap)
// The baffle spans from the divider to 7 mm short of the sensor-side end wall: the gap beside that wall is the only way up for the air that passed the sensor.
module baffle() {
    xa = x_div;  xb = Lo - t_end - g_gap;
    rbox(xa, xb, t_back-eps, Hbase_y, z_p0, z_p0+part_wall);
    rbox(xa, xb, t_back-eps, Hbase_y, z_p1-part_wall, z_p1);
    rbox(xb-part_wall, xb, t_back-eps, Hbase_y, z_p0, z_p1);          // end cap closes the air gap
}

// ---------------------------------------------------------------- vertical divider between the host column and the sensor / C6 column + wire slots
module divider() {
    rbox(x_div-div_t/2, x_div+div_t/2, t_back-eps, Hbase_y, z_s0-eps, z_u1+eps);
}
module divider_slot(zc) {
    y0 = t_back + 4;  rise = div_slot_h - 3;                         // 45-degree-class roof, no bridge > 6 mm
    translate([x_div - div_t/2 - 1, 0, 0]) rotate([90,0,90]) linear_extrude(height = div_t + 2)
        polygon([[y0, zc-div_slot_w/2], [y0, zc+div_slot_w/2], [y0+3, zc+div_slot_w/2],
                 [y0+3+rise, zc+div_slot_w/2-3], [y0+3+rise, zc-div_slot_w/2+3], [y0+3, zc-div_slot_w/2]]);
}

// ---------------------------------------------------------------- antenna seat (inside face of an end wall)
function xs(side, x) = (side==0) ? x : Lo - x;
module ant_seat(side) {
    d    = ant_seat_d;
    half = ant_w/2 + ant_seat_m + d;
    ylo  = ant_y - half;  yhi = ant_y + half;
    zl   = ant_z0 - ant_seat_m;  zh = ant_z1 + ant_seat_m;
    translate([0,0,zl]) linear_extrude(height=zh-zl)
        polygon([[xs(side,t_end+0.5), ylo-0.5], [xs(side,t_end-d), ylo+d],
                 [xs(side,t_end-d), yhi-d],     [xs(side,t_end+0.5), yhi+0.5]]);
}

// ---------------------------------------------------------------- wall mounting (R4)
module key_stadium(x, zh, y0, h, d) {
    hull() { cyl_y(x, zh, y0, h, d); cyl_y(x, zh + key_slot_l, y0, h, d); }
}
module key_chamber_solid(x, zh, yp) {            // sealed chamber behind the plate: ring wall + roof (bridge = cavity width 8.0)
    key_stadium(x, zh, yp-eps, key_cav_h + key_roof_t + eps, key_head_d + 2*key_cav_m + 2*key_ring_t);
}
module key_chamber_cut(x, zh, yp) {
    key_stadium(x, zh, yp-0.01, key_cav_h + 0.01, key_head_d + 2*key_cav_m);
    cyl_y(x, zh, -1, yp + 1.1, key_head_d);
    hull() { cyl_y(x, zh, -1, yp + 1.1, key_slot_w); cyl_y(x, zh + key_slot_l, -1, yp + 1.1, key_slot_w); }
}
module sh_cut(x, z, yp) {                         // countersunk wall-screw hole from inside, closed by a thin skin at the back
    cs_h = (sh_head_d - sh_d)/2/tan(sh_half);
    cyl_y(x, z, sh_skin, yp - sh_skin + 0.5, sh_d);
    translate([x, yp - cs_h, z]) rotate([-90,0,0]) cylinder(d1=sh_d, d2=sh_head_d, h=cs_h+eps, $fn=40);
}
module tape_cuts(xc, w, rib, n, d, z0, z1) {      // recess cells (each <= 10 mm wide: a recess is a bridge in print)
    for (i=[0:n-1]) {
        c = xc + (i - (n-1)/2)*(w + rib);
        rbox(c-w/2, c+w/2, -1, d, z0, z1);
    }
}

// ---------------------------------------------------------------- module centres
xmid_h = xh0 + xiao_w/2;                          // host column centre (= the USB-C opening)
xmid_c = xc0 + xiao_w/2;                          // C6 centre
xbme_c = (bme_x0 + bme_x1)/2;                     // sensor centre
y_usb  = ym_f + usb_h/2;
y_low  = y_usb - usb_open_h/2;                    // lower edge of the USB notch

// ---------------------------------------------------------------- BASE
module base_mounted() {
    difference() {
        union() {
            difference() {                         // rounded shell, open to the front
                outer_solid(0, Hbase_y, ch_back, snap_seam);
                cavity();
            }
            baffle();
            divider();
            for (hk = hooks) snap_bump(hk[0], hk[1], hk[2]);
            cradle(xh0, xh1, zh0, zh1, t_back, ym_b, xiao_pcb_t, clr, clip_ov);        // host, USB-C end down
            cradle(xc0, xc1, zc0, zc1, t_back, ym_b, xiao_pcb_t, clr, clip_ov);        // C6, USB-C end up (unused)
            cradle(bme_x0, bme_x1, bme_z0, bme_z1, t_back, bme_yb, bme_pcb_t, clr, clip_ov);
            if (keyholes_on == 1) {
                key_chamber_solid(key_xc, key_zh,  t_back);
                key_chamber_solid(key_xc2, key_zh2, t_back);
            }
        }
        // THE one USB-C opening: bottom wall, open to the lid side, facing down, with a smooth lead-in and cable-tie anchor slots
        usb_notch(xmid_h, usb_open_w, y_low, Hbase_y + 1, -1, z_s0 + 1.01);
        usb_leadin(xmid_h, usb_open_w, y_low, Hbase_y + 1, usb_lead);
        tie_slots(xmid_h, y_usb);
        divider_slot(div_s1_z);
        divider_slot(div_s2_z);
        ant_seat(0);
        ant_seat(1);
        louver([xbme_c, v_bot_y, z_s0], [0,1,0], [0,0,-1], s_len, v_bot_n, t_wall, louver_ang_wall);   // sensor inlet, faces down
        if (keyholes_on == 1) {
            key_chamber_cut(key_xc, key_zh,  t_back);
            key_chamber_cut(key_xc2, key_zh2, t_back);
        }
        if (sh_on == 1) { sh_cut(sh_x, sh_z, t_back); sh_cut(sh_x2, sh_z2, t_back); }
        if (dim_on == 1) dim_marks();
        if (tape_on == 1) tape_cuts(tape_xc, tape_w, tape_rib, tape_n, tape_d, tape_m, tape_z1);
        for (hk = hooks) snap_slot(hk[0], hk[1], hk[2]);                // release access: only through the back plate
    }
}

// ---------------------------------------------------------------- drilling marks on the back face (R17)
// Seen from the back (X runs left to right there), so the text needs no mirroring. Recess from the back face (y = 0) down to dim_depth.
module dim_marks() {
    rbox(key_xc - dim_w/2, key_xc2 + dim_w/2, -1, dim_depth, dim_z - dim_w/2, dim_z + dim_w/2);          // dimension line
    for (x = [key_xc, key_xc2]) rbox(x - dim_w/2, x + dim_w/2, -1, dim_depth, dim_ext_z1, dim_ext_z2);    // extension lines under the holes
    translate([Lo/2, dim_depth, dim_txt_z]) rotate([90, 0, 0]) linear_extrude(height = dim_depth + 1)
        offset(r = -0.4) offset(r = 0.4) text(dim_txt, size = dim_txt_size, font = name_font, halign = "center", valign = "baseline", spacing = 1.15, $fn = 16);
}

// ---------------------------------------------------------------- engraved name (R15) in the OUTER face of the lid
// 2D text in the viewer's reading orientation; seen from the front X runs right to left, so the text is mapped with x2 -> (x_text - x2).
// Stepped recess: one layer per 0.2 mm, outline offset by name_emb + 0.2*(k + 0.5), widest at the outer face = 45-degree walls (prints, since the lid prints outer face down).
module name2d(off) {
    cap = 0.72*name_size;
    // closing with r = 0.4 fills material islands / walls narrower than 0.8 mm (counters of the letters at the widest layer, gaps between letters)
    offset(r = -name_close) offset(r = name_close) offset(r = off) translate([0, -cap/2]) {
        translate([0,  name_pitch]) text(name_l1, size=name_size, font=name_font, halign="center", valign="baseline", spacing=name_spacing, $fn=16);
        text(name_l2, size=name_size, font=name_font, halign="center", valign="baseline", spacing=name_spacing, $fn=16);
        translate([0, -name_pitch]) text(name_l3, size=name_size, font=name_font, halign="center", valign="baseline", spacing=name_spacing, $fn=16);
    }
}
module name_cut(emb = name_emb, depth = name_depth, xt = 0, zt = 0) {
    n = round(depth/0.2);
    for (k = [0:n-1])
        multmatrix([[-1,0,0,xt],[0,0,1,Do - depth + 0.2*k],[0,1,0,zt],[0,0,0,1]])
            linear_extrude(height = 0.2 + ((k == n-1) ? 0.5 : 0.001)) name2d(emb + 0.2*(k + 0.5));
}

// ---------------------------------------------------------------- LID
module lid_mounted() {
    difference() {
        union() {
            outer_solid(Hbase_y, Do, snap_seam, ch_lid);
            for (hk = hooks) snap_hook(hk[0], hk[1], hk[2]);
        }
        // NO inlets in the lid: the air enters from below (bottom-wall louvres for the sensor column, the USB opening for the host column);
        // a low louvre would also stand in front of the host BOOT/RESET buttons (R16) and take the room of the engraved name (R15)
        // outlets, one group per column, angled down (each slat overhangs its slot)
        for (xc = [xmid_h, xmid_c])
            louver([xc, Hbase_y, v_out_zt - span_u(v_out_n, louver_ang_lid)], [0,0,1], [0,1,0],
                   v_out_len, v_out_n, t_lid, louver_ang_lid);
        // device name, centred on the lid
        name_cut(xt = Lo/2, zt = name_zc);
    }
}

// ---------------------------------------------------------------- print orientation transforms
module print_base() { translate([0, Ho, 0]) rotate([90,0,0]) base_mounted(); }
module print_lid()  { translate([0, 0, Do]) rotate([-90,0,0]) lid_mounted(); }     // outer face on the plate

// ---------------------------------------------------------------- FIT SAMPLES (coupons)
module print_xf(zmax) { translate([0, zmax, 0]) rotate([90,0,0]) children(); }       // base-like parts (Y up)

// 1) board cradle: three variants (clearance / lip overhang) + USB notch wall with 3 widths
module fit_modules() {
    pw = 31;
    print_xf(46) {
        difference() {
            union() {
                rbox(0, 3*pw, 0, 2, 0, 46);
                for (i=[0:2]) {
                    c  = (i==0) ? fs_clr1 : (i==1) ? fs_clr2 : fs_clr3;
                    ov = (i==0) ? fs_ov1  : (i==1) ? fs_ov2  : fs_ov3;
                    bx0 = 6.5 + pw*i;
                    cradle(bx0, bx0+xiao_w, 7, 7+xiao_l, 2, 2+h_post, xiao_pcb_t, c, ov);
                }
                rbox(0, 3*pw, 0, 14, 36, 36+t_wall);
            }
            for (i=[0:2]) {
                w = (i==0) ? fs_usb1 : (i==1) ? fs_usb2 : fs_usb3;
                usb_notch(pw*i + pw/2, w, 3.5, 15, 35, t_wall+2);
            }
        }
    }
}

// 2) antenna seat depth x3
module fit_antenna() {
    tile = ant_len + 2*ant_seat_m + 6;
    print_xf(3*tile) {
        difference() {
            union() { rbox(0, t_end, 0, 14, 0, 3*tile); rbox(-12, t_end, 0, 2, 0, 3*tile); }
            for (i=[0:2]) {
                d = (i==0) ? fs_seat1 : (i==1) ? fs_seat2 : fs_seat3;
                z0 = tile*i + 3;  half = ant_w/2 + ant_seat_m + d;
                translate([0,0,z0]) linear_extrude(height=ant_len+2*ant_seat_m)
                    polygon([[t_end+0.5, 7-half-0.5], [t_end-d, 7-half+d], [t_end-d, 7+half-d], [t_end+0.5, 7+half+0.5]]);
            }
        }
    }
}

// 4) lid snap hooks (R8): a case-side piece (wall + bumps + blind release slots) and a lid-side piece (plate + hooks) with three
//    head protrusions 0.8 / 1.0 / 1.2 mm.  Real geometry: same beam length (19 mm), same bump, same slot; the lid piece prints
//    outer face down like the real lid.  They mate in the mounted coordinates (xf = 2.0 wall face).
module fit_snap() {
    xf = 2.0;  zs = snap_b + 6;
    print_xf(3*zs) {
        difference() {
            union() {
                rbox(xf-2, xf+14, 0, t_back, 0, 3*zs);
                rbox(xf-2, xf, 0, Hbase_y, 0, 3*zs);
                for (i=[0:2]) snap_bump(xf, 1, 3 + zs*i);
            }
            for (i=[0:2]) snap_slot(xf, 1, 3 + zs*i);
        }
    }
    translate([30, 0, 0]) translate([0, 0, Do]) rotate([-90,0,0]) {
        rbox(xf, xf+14, Hbase_y, Do, 0, 3*zs);
        for (i=[0:2]) {
            h = (i==0) ? fs_h1 : (i==1) ? fs_h2 : fs_h3;
            snap_hook(xf, 1, 3 + zs*i, h);
        }
    }
}

// 5) engraved name test (R15): the word "gateway" (the widest line, with descenders) on three plate pieces printed outer face down, embolden 0.10 / 0.25 / 0.40 mm
module fit_name() {
    for (i = [0:2]) {
        e = (i == 0) ? fs_emb1 : (i == 1) ? fs_emb2 : fs_emb3;
        translate([0, 22*i, 0]) translate([0, 0, Do]) rotate([-90,0,0]) difference() {
            rbox(0, 76, Hbase_y, Do, 0, 20);
            name_one(e);
        }
    }
}
module name_one(emb) {
    n = round(name_depth/0.2);
    for (k = [0:n-1])
        multmatrix([[-1,0,0,38.03],[0,0,1,Do - name_depth + 0.2*k],[0,1,0,10.02],[0,0,0,1]])
            linear_extrude(height = 0.2 + ((k == n-1) ? 0.5 : 0.001))
                offset(r = -name_close) offset(r = name_close) offset(r = emb + 0.2*(k + 0.5)) translate([0, -0.26*name_size])
                    text(name_l3, size=name_size, font=name_font, halign="center", valign="baseline", spacing=name_spacing, $fn=16);
}

// 6) louvre angle test in a STANDING wall
module fit_louvre() {
    print_xf(2.4+12) {
        difference() {
            union() { rbox(0, 66, 0, 22, 12, 12+t_wall); rbox(0, 66, 0, 2, 0, 12+t_wall); }
            for (i=[0:2]) {
                a = (i==0) ? fs_ang1 : (i==1) ? fs_ang2 : fs_ang3;
                louver([22*i+11, 5, 12], [0,1,0], [0,0,1], 16, 3, t_wall, a);
            }
        }
    }
}

// 7) mounting: sealed keyhole chamber, countersunk screw hole with skin, three tape-recess cell widths (bridge test)
module fit_mount() {
    print_xf(70) {
        difference() {
            union() { rbox(0, 90, 0, t_back, 0, 70); key_chamber_solid(70, 14, t_back); }
            key_chamber_cut(70, 14, t_back);
            sh_cut(70, 55, t_back);
            for (i=[0:2]) {
                w  = (i==0) ? fs_tape1 : (i==1) ? fs_tape2 : fs_tape3;
                x0 = (i==0) ? 4 : (i==1) ? 4 + fs_tape1 + tape_rib : 4 + fs_tape1 + fs_tape2 + 2*tape_rib;
                rbox(x0, x0 + w, -1, tape_d, 15, 55);
            }
        }
    }
}

// ---------------------------------------------------------------- dispatch
if      (part == "base")         print_base();
else if (part == "lid")          print_lid();
else if (part == "base_mounted") base_mounted();
else if (part == "lid_mounted")  lid_mounted();
else if (part == "fit_modules")  fit_modules();
else if (part == "fit_antenna")  fit_antenna();
else if (part == "fit_snap")     fit_snap();
else if (part == "fit_name")     fit_name();
else if (part == "fit_louvre")   fit_louvre();
else if (part == "fit_mount")    fit_mount();
