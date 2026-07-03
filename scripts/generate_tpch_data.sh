#!/usr/bin/env bash
# Generates TPC-H '.tbl' files at the requested scale factor using tpch-dbgen.
# Usage: bash scripts/generate_tpch_data.sh <scale_factor>
#
# Prereq: clone and build https://github.com/electrum/tpch-dbgen into
#         external/tpch-dbgen (path configurable in config/config.yaml).

set -euo pipefail

SCALE_FACTOR="${1:-1}"
DBGEN_DIR="external/tpch-dbgen"
OUT_DIR="data/raw/sf${SCALE_FACTOR}"

if [ ! -x "${DBGEN_DIR}/dbgen" ]; then
  echo "dbgen binary not found at ${DBGEN_DIR}/dbgen"
  echo "Build it first: git clone https://github.com/electrum/tpch-dbgen ${DBGEN_DIR} && (cd ${DBGEN_DIR} && make)"
  exit 1
fi

mkdir -p "${OUT_DIR}"
pushd "${DBGEN_DIR}" > /dev/null
./dbgen -f -s "${SCALE_FACTOR}"
mv ./*.tbl "../../${OUT_DIR}/"
popd > /dev/null

echo "Generated TPC-H SF-${SCALE_FACTOR} data into ${OUT_DIR}/"
