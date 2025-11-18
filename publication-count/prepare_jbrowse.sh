#!/usr/bin/env bash
set -euo pipefail

########################################
# 使い方
########################################
usage() {
  echo "Usage: $0 [--verbose] <ASSEMBLY1> [<ASSEMBLY2> ...]"
  exit 1
}

########################################
# オプション解析
########################################
VERBOSE=0
ASSEMBLIES=()

for arg in "$@"; do
  case "$arg" in
    --verbose)
      VERBOSE=1
      ;;
    -*)
      echo "Unknown option: $arg"
      usage
      ;;
    *)
      ASSEMBLIES+=("$arg")
      ;;
  esac
done

if [[ ${#ASSEMBLIES[@]} -eq 0 ]]; then
  usage
fi

########################################
# パス設定
########################################
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

JBROWSE_HOME="$HOME/jbrowse"
JBROWSE_DIR="$JBROWSE_HOME/jbrowse2"
ASSEMBLY_DIR="${JBROWSE_DIR}/assemblies"

LOG_DIR="${SCRIPT_DIR}/logs/prepare_jbrowse"
mkdir -p "${LOG_DIR}"
SUMMARY_LOG="${LOG_DIR}/summary.log"

SUCCESS_LIST=()
FAILED_LIST=()
SKIPPED_LIST=()

########################################
# メイン処理
########################################
for ASSEMBLY in "${ASSEMBLIES[@]}"; do
  echo "============================================"
  echo " Processing ${ASSEMBLY}"
  echo "============================================"

  # 既存チェック
  EXISTING_FASTA=$(find "${ASSEMBLY_DIR}" -maxdepth 1 -name "${ASSEMBLY}*genomic.fna" 2>/dev/null || true)

  if [[ -n "${EXISTING_FASTA}" ]]; then
    echo "[SKIP] ${ASSEMBLY} は既に登録されています"
    SKIPPED_LIST+=("${ASSEMBLY}")
    continue
  fi

  ########################################
  # 実行コマンド構築（verbose の有無に応じて）
  ########################################
  CMD=("${SCRIPT_DIR}/prepare_jbrowse_single.sh")
  [[ $VERBOSE -eq 1 ]] && CMD+=("--verbose")
  CMD+=("${ASSEMBLY}")

  ########################################
  # 実行 & 結果判定
  ########################################
  if "${CMD[@]}"; then
    SUCCESS_LIST+=("${ASSEMBLY}")
  else
    FAILED_LIST+=("${ASSEMBLY}")
  fi

done

########################################
# Summary（標準出力）
########################################
echo
echo "============================================"
echo " Summary"
echo "============================================"

echo "Success:"
if [[ ${#SUCCESS_LIST[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for item in "${SUCCESS_LIST[@]}"; do
    echo "  - $item"
  done
fi

echo
echo "Skipped:"
if [[ ${#SKIPPED_LIST[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for item in "${SKIPPED_LIST[@]}"; do
    echo "  - $item"
  done
fi

echo
echo "Failed:"
if [[ ${#FAILED_LIST[@]} -eq 0 ]]; then
  echo "  (none)"
else
  for item in "${FAILED_LIST[@]}"; do
    echo "  - $item"
  done
fi

echo "============================================"

########################################
# Summary（ログファイルへ追記）
########################################
{
  echo
  echo "===== Run at $(date '+%Y-%m-%d %H:%M:%S') ====="
  echo "Success:"
  if [[ ${#SUCCESS_LIST[@]} -eq 0 ]]; then
    echo "  (none)"
  else
    for item in "${SUCCESS_LIST[@]}"; do
      echo "  - $item"
    done
  fi

  echo
  echo "Skipped:"
  if [[ ${#SKIPPED_LIST[@]} -eq 0 ]]; then
    echo "  (none)"
  else
    for item in "${SKIPPED_LIST[@]}"; do
      echo "  - $item"
    done
  fi

  echo
  echo "Failed:"
  if [[ ${#FAILED_LIST[@]} -eq 0 ]]; then
    echo "  (none)"
  else
    for item in "${FAILED_LIST[@]}"; do
      echo "  - $item"
    done
  fi

  echo "======================================="
} >> "${SUMMARY_LOG}"