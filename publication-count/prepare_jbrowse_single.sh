#!/usr/bin/env bash
set -euo pipefail

########################################
# オプション解析（--verbose）
########################################
VERBOSE=0

if [[ "${1:-}" == "--verbose" ]]; then
  VERBOSE=1
  shift
fi

########################################
# 引数チェック
########################################
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 [--verbose] <ASSEMBLY_ACCESSION>"
  exit 1
fi

ASSEMBLY="$1"

########################################
# パス設定
########################################
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PUBCOUNT_DIR="$SCRIPT_DIR"

JBROWSE_HOME="$HOME/jbrowse"
JBROWSE_DIR="$JBROWSE_HOME/jbrowse2"
ASSEMBLY_DIR="${JBROWSE_DIR}/assemblies"

DATASET_TEMP_DIR="${SCRIPT_DIR}/ncbi_dataset"
DATA_ROOT="${DATASET_TEMP_DIR}/ncbi_dataset/data/${ASSEMBLY}"

# ログ保存先
LOG_DIR="${SCRIPT_DIR}/logs/prepare_jbrowse"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/${ASSEMBLY}.log"

# ログ出力
exec > >(tee -a "${LOG_FILE}") 2>&1

########################################
# log 関数
########################################
log() {
  echo -e "\n[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

########################################
# config.ini 存在確認
########################################
if [[ ! -f "${PUBCOUNT_DIR}/config.ini" ]]; then
  echo "Error: config.ini が見つかりません。事前に作成してください。"
  exit 1
fi

########################################
# 既存チェック（JBrowse 内）
########################################
EXISTING_FASTA=$(find "${ASSEMBLY_DIR}" -maxdepth 1 -name "${ASSEMBLY}*genomic.fna" 2>/dev/null || true)

if [[ -n "${EXISTING_FASTA}" ]]; then
  log "[SKIP] ${ASSEMBLY} は既に JBrowse に登録されています。"
  exit 0
fi

########################################
# stdout / stderr の扱い
########################################
# stdout：verbose のときだけ表示、verbose=0 は捨てる
# stderr：常に「画面＋ログ」に出す（tee）
stdout_redirect() {
  if [[ $VERBOSE -eq 1 ]]; then
    cat        # stdout をそのまま画面へ
  else
    cat >/dev/null   # stdout は捨てる
  fi
}

stderr_redirect() {
  # ダウンロードなどの進捗バーはログに含めず、ログ肥大化を防止。
  grep -v -E $'Collecting|Downloading|\\[1A|\\[2K|%[[:space:]][0-9]+/[0-9]+' \
    | tee -a "${LOG_FILE}"
}

########################################
# Step 1: GFF 作成
########################################
log "Step 1: Run publication-count-gff"

GFF_OUTPUT="${ASSEMBLY}_output.gff"

python "${PUBCOUNT_DIR}/publication-count-gff.py" -i "${ASSEMBLY}" \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

########################################
# Step 2: FASTA ダウンロード
########################################
log "Step 2: Download FASTA using NCBI datasets"

datasets download genome accession "${ASSEMBLY}" --include genome \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

unzip -o ncbi_dataset.zip -d "${DATASET_TEMP_DIR}" \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

########################################
# Step 3: FASTA検出 & .fai 作成
########################################
log "Step 3: Detect FASTA and create .fai"

FASTA=$(find "${DATA_ROOT}" -maxdepth 1 -name "*_genomic.fna" | head -n 1)
if [[ -z "${FASTA}" ]]; then
  echo "Error: *_genomic.fna が見つかりません。datasets の出力構造を確認してください。"
  exit 1
fi

samtools faidx "${FASTA}" \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

FAI="${FASTA}.fai"

########################################
# Step 4: JBrowse プロジェクト準備
########################################
log "Step 4: Prepare JBrowse project"

mkdir -p "${JBROWSE_HOME}"
if [[ ! -d "${JBROWSE_DIR}" ]]; then
  jbrowse create "${JBROWSE_DIR}" \
    1> >(stdout_redirect) \
    2> >(stderr_redirect)
fi

mkdir -p "${JBROWSE_DIR}/assemblies" "${JBROWSE_DIR}/tracks"

cp "${FASTA}" "${FAI}" "${JBROWSE_DIR}/assemblies/"
cp "${PUBCOUNT_DIR}/${GFF_OUTPUT}" "${JBROWSE_DIR}/tracks/"

cd "${JBROWSE_DIR}"

FASTA_BASENAME=$(basename "${FASTA}")
ASSEMBLY_NAME="${FASTA_BASENAME}"

########################################
# Step 5: Assembly 追加
########################################
log "Step 5: Add assembly"

jbrowse add-assembly "assemblies/${ASSEMBLY_NAME}" --load inPlace \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

########################################
# Step 6: GFF トラック追加
########################################
log "Step 6: Add GFF track"

jbrowse add-track "tracks/${GFF_OUTPUT}" \
  --assemblyNames "${ASSEMBLY_NAME}" \
  --load inPlace \
  --name "Gene annotation" \
  --trackId "${ASSEMBLY}_gff" \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

########################################
# Step 7: BigWig 作成、トラック追加
########################################
log "Step 7: Create and add BigWig track"

CHROMSIZES="${ASSEMBLY}.chrom.sizes"
BEDGRAPH="${ASSEMBLY}_output.bedGraph"
BEDGRAPH2="${ASSEMBLY}_output.noOverlap.bedGraph"
BIGWIG="tracks/${ASSEMBLY}_output.bw"

cut -f1,2 "assemblies/${FASTA_BASENAME}.fai" > "${CHROMSIZES}"

awk -F'\t' 'BEGIN{OFS="\t"} tolower($3)=="gene" && $6!="." {print $1, $4-1, $5, $6}' \
  "tracks/${GFF_OUTPUT}" \
  | sort -k1,1 -k2,2n \
  > "${BEDGRAPH}"

LC_ALL=C sort -k1,1 -k2,2n "${BEDGRAPH}" \
| awk -F'\t' 'BEGIN{OFS="\t"}
  /^#/ {next}
  {
    chr=$1; s=$2+0; e=$3+0; v=$4
    if (chr!=prev_chr) { prev_chr=chr; prev_end=0 }
    if (s < prev_end) s = prev_end
    if (s < e) { print chr, s, e, v; prev_end = e }
  }' > "${BEDGRAPH2}"

bedGraphToBigWig "${BEDGRAPH2}" "${CHROMSIZES}" "${BIGWIG}" \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

jbrowse add-track "${BIGWIG}" \
  --assemblyNames "${ASSEMBLY_NAME}" \
  --load inPlace \
  --name "Publication count" \
  --trackId "${ASSEMBLY}_bw" \
  1> >(stdout_redirect) \
  2> >(stderr_redirect)

########################################
# 一時ファイル削除
########################################
log "Cleaning up temporary files"

rm -rf "${DATASET_TEMP_DIR}"
rm -f "${SCRIPT_DIR}/ncbi_dataset.zip"
rm -f "${PUBCOUNT_DIR}/${GFF_OUTPUT}"
rm "${CHROMSIZES}" "${BEDGRAPH}" "${BEDGRAPH2}"

########################################
log "All steps completed successfully."
echo
########################################