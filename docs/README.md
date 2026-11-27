# docs/ — knowledge base

Start with `../AGENTS.md` (rules, layout, commands). Then:

| Document | Topic |
|---|---|
| [DEPENDENCIES_AND_OTA.md](DEPENDENCIES_AND_OTA.md) | are all libraries reachable (licences, versions, IDF per esp-matter branch), OTA of the host and of the C6 over Wi-Fi, BSEC licence |
| [ENVIRONMENT.md](ENVIRONMENT.md) | the verified toolchain (Windows 11 + WSL2 Ubuntu 26.04, IDF, KiCad 10, Python), installing a new ESP-IDF side by side |
| [BUILD_AND_FLASH.md](BUILD_AND_FLASH.md) | building two images in WSL, merged images, flashing two boards from Windows, serial monitor |
| [TESTING.md](TESTING.md) | host unit tests (C), tool tests (pytest), mutation checks, build regression, hardware test list |
| [CODING_GUIDELINES.md](CODING_GUIDELINES.md) | pure-logic split, per-target pins, inter-chip link, secrets/NVS, style, licences |
| [HARDWARE_KICAD.md](HARDWARE_KICAD.md) | KiCad workflow, LCSC fields, headless JLCPCB export, iBOM, XIAO pinouts, design requirements |
| [ENCLOSURE_3D.md](ENCLOSURE_3D.md) | 3D-printing rules (owner's checklist) and gateway-specific enclosure inputs |
| [MCU_NOTES.md](MCU_NOTES.md) | ESP32-S3 / C6 / C3 / ESP32: ADC, peripherals, pins, IDF support (verified vs. unverified) |
| [LESSONS_LEARNED.md](LESSONS_LEARNED.md) | symptom → cause → fix table from the previous project |
| [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md) | decisions the owner still has to make |

Also in the repository root: `project_specification_and_requirements.md` (project intent, hardware spec and requirements, Polish), `Bramka Smarthome na ESP32-C6.pdf` (AI research export — **unverified** claims),
`wytyczne_projektowania_druk3d (1).md` (3D-print checklist, Polish). `../scripts/README.md` documents the helper scripts.

**Documentation policy:** every document ends with `## References` (primary sources: datasheets, vendor docs, standards by number); "verified" means checked on the
owner's machine on the date given, "unverified" means taken from the PDF or memory; one source of truth per value (the KiCad schematic for components, the pin header for GPIOs).

## References

- Previous project's docs (same author, same tooling): `../../wireless-esp8266-dap/docs/`
