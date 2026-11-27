# Pure-C logic shared by the images and compiled on the host by tests/unit/Makefile.
# Keep this file free of target-specific logic (docs/CODING_GUIDELINES.md section 2).
# tests/unit/test_firmware_layout.py fails if a .c file in this directory is missing from SRCS.
# The component is named "common" (IDF uses the directory name). Images that use it list ../common in
# EXTRA_COMPONENT_DIRS; scripts/wsl_idf.sh mirrors this directory next to the project copy.
idf_component_register(
    SRCS
        "gw_bthome.c"
        "gw_rcp_supervisor.c"
        "gw_report.c"
        "gw_sensor_table.c"
        "gw_units.c"
        "gw_ventilation.c"
    INCLUDE_DIRS ".")
