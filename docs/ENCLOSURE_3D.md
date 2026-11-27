# 3D-printed enclosure

The authoritative print rules are the owner's own checklist **`wytyczne_projektowania_druk3d (1).md`** (Polish, in the repo root;
lessons from furniture templates, drill stops and bathroom-cabinet sliding rails). This page does not replace it — it condenses
the rules an agent must not violate, and adds the gateway-specific parts. When the two disagree, the owner's file wins; fix this page.
Suggestion to the owner: move that file to `docs/3d-printing-guidelines.pl.md` (not done — it is the owner's file).

## 1. Printer and material (from the owner's guidelines)

* **Bambu Lab H2D**, 0.4 mm nozzle, **Textured PEI** plate; slicer Bambu Studio.
* **White PETG Basic** preferred (humid rooms, warmth, screws do not crack); white PLA Basic acceptable at room temperature, away from heat.
  Profiles "Bambu PETG Basic" / "Bambu PLA Basic". **One material for the whole set** (shrinkage differs); **fit samples from the same filament** as the final parts.
* Structural parts: **4 walls, ~30 % infill, 0.2 mm layers**; visible plugs/curves 0.12 mm; seam on a hidden wall; part length ≤ ~240 mm (otherwise split with a joint).

## 2. Rules that decide whether a part prints (checklist form)

1. **Concept first, files second:** sketch sections, joints and the assembly order → owner approves → only then STL.
2. **No supports:** overhangs ≤ 45°; horizontal holes ≤ ~Ø8 (larger → vertical orientation or teardrop); bridges ≤ ~10 mm and supported on both sides; channels/grooves open
   to the top in the print orientation; the orientation is **fixed by the STL** — do not rotate it in the slicer.
3. **Walls ≥ 1.5–2 mm** (≈ 4 lines of a 0.4 nozzle); < 0.8 mm the slicer drops or isolates them. A joint must not cut through channels/holes (it falls apart into thin slivers).
   Wall around a screw/plug seat ≥ 1 mm. Inspect layer sections every 0.2–0.4 mm in the slicer preview.
4. **Mesh quality of the *saved* STL:** 0 open edges, 0 non-manifold edges, 0 reversed faces. "Repaired/open edges" in Bambu Studio means: fix at the source and re-import — do not print.
5. **Fits (0.4 nozzle), starting values:** M3 through-hole Ø3.6; M3 nut pocket 5.9 × 3.4 (open towards the printable side); drilled bushing = drill + 0.3; press-fit plugs tested at three
   diameters (e.g. Ø8.05 / 7.95 / 7.85 for a Ø8.2 seat); 3 mm sheet slot 3.7; printed Ø3 pin → Ø3.25 hole. **Always print a fit sample (3 clearance variants) before the full set.**
6. **Screws:** never self-tap into the plastic (exception: M3 into a printed nut seat); screws pass through printed parts into the carrier.
7. **Recompute mating parts after every change** (the old project's plexiglass size changed after a groove depth change).
8. **Pre-send checklist** (copy into the part's README): concept accepted · assembly possible in the real place · no supports in the given orientation · no wall < 1.5 mm / orphan features ·
   no collisions in the assembled model · watertight saved STL · fit samples included · part ≤ ~240 mm · mating parts recomputed · print settings stated.

## 3. Gateway-specific design inputs

| Topic | Requirement / suggestion | Status |
|---|---|---|
| PCB and modules | Get an exact 3D model from KiCad: `kicad-cli pcb export step --subst-models --drill-origin … gw.kicad_pcb` (modules, connectors, holes; `--board-only` for just the board, `--no-dnp` to leave out unpopulated parts). Use the STEP as the reference body in CAD; re-export after every PCB change | verified: command and options exist in KiCad 10 |
| Mounting | M3 standoffs/bosses from the PCB holes (position taken from the STEP). Keep ≥ 1 mm wall around screw seats. Check the PCB-to-lid clearance of tall parts (pin headers, U.FL/SMA, USB-C) | to do |
| Antennas | **Update 2026-11-26: two adhesive FPC antennas, 2J Antennas `2JF0802P-010MC137-UFL` (39.6 × 8.4 × 0.2 mm, 10 cm U.FL cable), glued to the *inside* of two opposite plastic walls — no SMA bulkheads, no holes.** Keep a flat, smooth wall surface for the adhesive (≥ 45 × 15 mm, no ribs), no metal/conductive filament/foil near the antenna, thin wall (PETG, ≈ 1.5–2 mm); the 10 cm cable limits the module-to-wall distance. Inner length between the antenna walls ≈ 10 cm = the antenna separation (the earlier plan: *two external 2.4 GHz antennas on SMA bulkheads*, on opposite faces, vertical and collinear — kept only as a fallback; the sentence below applies to it). **Owner's decision 2026-11-26: small enclosure, centre-to-centre ≈ 10 cm, less acceptable but not below ≈ 6 cm** (centre distance ≈ inner height H + (L₁+L₂)/2 with L = antenna length above the wall; H ≈ 5–6 cm with 5 cm antennas gives ≈ 10 cm — to confirm in CAD; reasoning in `project_specification_and_requirements.md`, decision 4; **measure** Zigbee packet loss). Hole size and flat/nut clearance **from the chosen bulkhead's datasheet** (do not guess); allow room to tighten the nut and to bend the pigtail (min. bend radius). The enclosure must not shield the antennas: keep them outside, or use plastic only near them | to do |
| BME680 | Needs **air exchange** and **thermal isolation** from the modules/regulators: separate chamber with slots/vents (keep vents ≥ 1.5 mm for printability and screen out dust), a gap or thermal break to the electronics, sensor away from the warm side/lid, airflow path from outside to the sensor and *not* over the processors. Print the chamber walls ≥ 2 mm. Verify by logging temperature after power-on (TESTING §6) | to do |
| Heat | Let the modules' heat escape: vents at the bottom/top for convection (no supports: use 45° louvres); measure the case temperature once the real power draw is known. PETG tolerates more than PLA; PLA softens near ~60 °C (general knowledge) | to do |
| Access | USB-C opening (service + power), pin-hole access to **BOOT/RESET** of both modules, light pipe or window for the status LED, label recess (serial number, setup QR for Matter — keep the QR printable and readable) | to do |
| Mounting to the wall/shelf | keyholes or screw ears; printed on the face that sits on the plate | to do |
| Assembly | The lid closes **last**; modules and cables must be insertable and serviceable with the enclosure installed (the old checklist's "closing element" rule). Prefer screws over snap fits for a service product; print a snap-fit test strip if snaps are used | to do |

## 4. Workflow

```text
KiCad PCB ──kicad-cli pcb export step──► gw.step ─┐
SMA bulkhead / USB-C / LED STEP (vendor models) ──┴─► CAD (tool: open decision) ─► fit samples ─► STL per part (orientation fixed) ─► Bambu Studio ─► print
                                                                  └─ assembly check (collisions, wire/bend radius) ─► checklist ─► release
```

* Parametrise the key dimensions (PCB outline, hole positions, wall thickness, clearances) so a PCB revision is an edit, not a redraw.
* Store source CAD **and** STEP/STL in `hardware/enclosure-3d/` (large binaries: consider Git LFS or release assets; `.gitattributes` already marks `*.stl|step|3mf` as binary).
* Name parts with a revision (`enclosure_base_rev03.stl`) and record the matching PCB tag; list print settings next to each STL (material, walls, infill, layer height, orientation, supports: none).
* Keep a log of printed fit samples (clearance chosen, material, date) — they decide the final tolerances.

## 5. Open points

CAD tool (FreeCAD / Fusion / other?), final dimensions, antenna connector type and positions, wall-mount vs desk, colour/finish — see `OPEN_QUESTIONS.md`.

## References

- Owner's guidelines: `wytyczne_projektowania_druk3d (1).md` (this repository)
- KiCad CLI 3D export (`kicad-cli pcb export step|stl|glb|render`, checked with `--help` in KiCad 10): <https://docs.kicad.org/>
- Bambu Lab H2D / Bambu Studio documentation: <https://wiki.bambulab.com/>
- SMA bulkhead connector dimensions: take them from the datasheet of the part chosen for the BOM
- Bosch BME680 datasheet (thermal/self-heating notes, mounting): <https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme680/>
