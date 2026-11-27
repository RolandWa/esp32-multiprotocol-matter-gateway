#!/bin/bash
# Build an ESP-IDF project that lives on the Windows file system, inside WSL.
#
# Why this exists (hard-won, see docs/LESSONS_LEARNED.md):
#   * ESP-IDF / cmake / kconfiglib break on paths with spaces or commas - the repo
#     lives in a OneDrive folder - so the sources are rsync'ed to a clean Linux path.
#   * Each (IDF version, target) pair gets its own build dir so builds never mix.
#   * IDF's export.sh must NOT be sourced under `set -u`.
#   * IDF v4.4.2 needs Python <= 3.10 (a python3 -> python3.10 shim is put on PATH).
#
# Usage (inside WSL, or via scripts/build.bat from Windows):
#   wsl_idf.sh --project <dir> --target <chip> [--idf <dir>] [--python <exe>]
#              [--work <dir>] [--merge] [--clean] [-- idf.py args ...]
#
#   --project  project dir with the top-level CMakeLists.txt (absolute, or relative
#              to the repository root)
#   --target   esp32s3 | esp32c6 | esp32c3 | esp32 | ...   (set-target is run once per build dir)
#   --idf      ESP-IDF checkout (default: $IDF_DIR)
#   --python   python for IDF's venv detection (default: python3.10 for IDF v4.x, else python3)
#   --work     where sources and build dirs live (default: $HOME/work)
#   --extra-export <file>
#              sourced after IDF's export.sh, e.g. ~/esp/esp-matter/export.sh for esp-matter builds
#              (or set EXTRA_EXPORT)
#   --tools-path <dir>
#              IDF_TOOLS_PATH for this build only (exported inside the build subshell, never globally),
#              e.g. ~/.espressif-gateway for the side-by-side IDF v6.0.x - so the old project's
#              ~/.espressif is neither used nor modified (or set GW_IDF_TOOLS_PATH)
#   --merge    after a successful build, write <project>/dist/<target>/<name>_full.bin
#              (+ _app.bin) next to the sources on the Windows side
#   --clean    delete this target's build dir first
#   idf.py args default to: build
#
# Examples:
#   wsl_idf.sh --project firmware/host-esp32s3 --target esp32s3 --idf ~/esp/esp-idf-v5.x --merge
#   wsl_idf.sh --project firmware/rcp-esp32c6  --target esp32c6 --idf ~/esp/esp-idf-v5.x -- build size

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT=""; TARGET=""; IDF="${IDF_DIR:-}"; PY="${PYTHON_FOR_IDF:-}"; WORK="$HOME/work"
EXTRA="${EXTRA_EXPORT:-}"; TOOLS="${GW_IDF_TOOLS_PATH:-}"; MERGE=0; CLEAN=0; IDF_ARGS=()

while [ $# -gt 0 ]; do
  case "$1" in
    --project) PROJECT="$2"; shift 2;;
    --target)  TARGET="$2";  shift 2;;
    --idf)     IDF="$2";     shift 2;;
    --python)  PY="$2";      shift 2;;
    --work)    WORK="$2";    shift 2;;
    --extra-export) EXTRA="$2"; shift 2;;
    --tools-path)   TOOLS="$2"; shift 2;;
    --merge)   MERGE=1;      shift;;
    --clean)   CLEAN=1;      shift;;
    --)        shift; IDF_ARGS=("$@"); break;;
    -h|--help) sed -n '2,36p' "$0"; exit 0;;
    *)         IDF_ARGS+=("$1"); shift;;
  esac
done
[ ${#IDF_ARGS[@]} -eq 0 ] && IDF_ARGS=(build)

die() { echo "ERROR: $*" >&2; exit 1; }
[ -n "$PROJECT" ] || die "--project is required"
[ -n "$TARGET" ]  || die "--target is required"
[ -n "$IDF" ]     || die "--idf <dir> (or IDF_DIR) is required"
# expand a leading ~ (the shell does not do it for values received via arguments)
IDF="${IDF/#\~/$HOME}"; WORK="${WORK/#\~/$HOME}"; PROJECT="${PROJECT/#\~/$HOME}"; EXTRA="${EXTRA/#\~/$HOME}"; TOOLS="${TOOLS/#\~/$HOME}"
[ -z "$TOOLS" ] || [ -d "$TOOLS" ] || die "--tools-path directory not found: $TOOLS (run install.sh with IDF_TOOLS_PATH set first)"
[ -z "$EXTRA" ] || [ -f "$EXTRA" ] || die "--extra-export file not found: $EXTRA"
[ -f "$IDF/export.sh" ] || die "no export.sh in $IDF"
case "$PROJECT" in /*) ;; *) PROJECT="$REPO_ROOT/$PROJECT";; esac
[ -f "$PROJECT/CMakeLists.txt" ] || die "no CMakeLists.txt in $PROJECT"
PROJECT="$(cd "$PROJECT" && pwd)"

# Python shim: IDF v4.x cannot use the system python3 (3.11+ breaks its requirements)
IDF_TAG="$(git -C "$IDF" describe --tags 2>/dev/null || basename "$IDF")"
if [ -z "$PY" ]; then
  case "$IDF_TAG" in v4.*) PY="python3.10";; *) PY="python3";; esac
fi
SHIM="$HOME/.idf_python_shim_$(echo "$PY" | tr -c 'A-Za-z0-9\n' '_')"
mkdir -p "$SHIM"
ln -sf "$(command -v "$PY")" "$SHIM/python3"
ln -sf "$(command -v "$PY")" "$SHIM/python"

NAME="$(basename "$PROJECT")"
SRC="$WORK/src/$NAME"
BLD="$WORK/build/$NAME/${IDF_TAG//[^A-Za-z0-9._-]/_}-$TARGET"
mkdir -p "$SRC" "$BLD"
[ "$CLEAN" = 1 ] && { echo "== cleaning $BLD"; rm -rf "$BLD"; mkdir -p "$BLD"; }

echo "== project : $PROJECT"
echo "== sources : $SRC   (rsync copy, space-free path)"
echo "== build   : $BLD"
echo "== idf     : $IDF ($IDF_TAG)   python: $PY ($("$PY" --version 2>&1))"
echo "== target  : $TARGET"

# Excluded patterns are also protected from --delete (generated state stays in WSL)
rsync -a --delete \
  --exclude=.git/ --exclude=.venv/ --exclude=__pycache__/ --exclude=.claude/ \
  --exclude=build/ --exclude=dist/ --exclude=managed_components/ \
  --exclude=sdkconfig --exclude=sdkconfig.old \
  "$PROJECT/" "$SRC/" || die "rsync failed"

# Projects reach the shared pure-C component as ../common (EXTRA_COMPONENT_DIRS), so a sibling
# "common" directory is mirrored next to the project copy ($WORK/src/common) on every build.
SHARED="$(dirname "$PROJECT")/common"
if [ -d "$SHARED" ]; then
  mkdir -p "$WORK/src/common"
  rsync -a --delete "$SHARED/" "$WORK/src/common/" || die "rsync of $SHARED failed"
  echo "== shared   : $SHARED -> $WORK/src/common"
fi

# Source IDF in a subshell, without `set -u`
(
  export PATH="$SHIM:$PATH"
  [ -z "$TOOLS" ] || export IDF_TOOLS_PATH="$TOOLS"
  . "$IDF/export.sh" > /dev/null 2>&1 || die "sourcing $IDF/export.sh failed (run install.sh for $TARGET?)"
  if [ -n "$EXTRA" ]; then . "$EXTRA" > /dev/null 2>&1 || die "sourcing $EXTRA failed"; fi

  CURRENT="$(grep -E '^IDF_TARGET:' "$BLD/CMakeCache.txt" 2>/dev/null | cut -d= -f2)"
  if [ "$CURRENT" != "$TARGET" ]; then
    echo "== idf.py set-target $TARGET"
    idf.py -C "$SRC" -B "$BLD" set-target "$TARGET" || die "set-target failed"
  fi

  echo "== idf.py ${IDF_ARGS[*]}"
  idf.py -C "$SRC" -B "$BLD" "${IDF_ARGS[@]}" || exit $?

  # The component manager writes dependencies.lock in the WSL copy; the lock in the project is what pins versions.
  if [ -f "$SRC/dependencies.lock" ] && ! cmp -s "$SRC/dependencies.lock" "$PROJECT/dependencies.lock" 2>/dev/null; then
    echo "== NOTE: dependencies.lock is new/changed - pin it and commit it:"
    echo "     cp \"$SRC/dependencies.lock\" \"$PROJECT/dependencies.lock\""
  fi

  if [ "$MERGE" = 1 ]; then
    [ -f "$BLD/flash_args" ] || die "no $BLD/flash_args (did the build run?)"
    OUT="$PROJECT/dist/$TARGET"; mkdir -p "$OUT"
    APP="$(ls "$BLD"/*.bin 2>/dev/null | grep -v -E 'bootloader|partition|_full|ota_data' | head -1)"
    ( cd "$BLD" && esptool.py --chip "$TARGET" merge_bin -o "$OUT/${NAME}_full.bin" @flash_args ) \
      || die "merge_bin failed"
    [ -n "$APP" ] && cp -f "$APP" "$OUT/${NAME}_app.bin"
    echo "== merged image : $OUT/${NAME}_full.bin ($(stat -c %s "$OUT/${NAME}_full.bin") bytes)"
    [ -n "$APP" ] && echo "== app image    : $OUT/${NAME}_app.bin ($(stat -c %s "$OUT/${NAME}_app.bin") bytes)"
  fi
)
exit $?
