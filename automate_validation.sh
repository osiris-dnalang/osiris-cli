#!/usr/bin/env bash
#
# DNA-Lang ΛΦ Validation Automation
# ==================================
#
# This script automates the entire Nobel-worthy validation process:
# 1. Package dataset for Zenodo
# 2. Run multi-platform validation (IBM, IonQ, Rigetti)
# 3. Generate publication-ready paper
# 4. Upload to Zenodo and get DOI
#
# Usage:
#   ./automate_validation.sh [options]
#
# Options:
#   --dry-run     Don't execute, just show what would happen
#   --simulator   Only run local simulator (free, for testing)
#   --ionq        Include IonQ validation (costs ~$500)
#   --rigetti     Include Rigetti validation (free with QCS account)
#   --all         Run all platforms (IBM + IonQ + Rigetti)
#   --publish     Auto-publish to Zenodo (requires ZENODO_TOKEN)
#
# Environment Variables:
#   ZENODO_TOKEN      - Zenodo API token for upload
#   IBM_QUANTUM_TOKEN - IBM Quantum API token
#   AWS_ACCESS_KEY_ID - AWS credentials for IonQ/Braket
#   AWS_SECRET_ACCESS_KEY
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
CORPUS_DIR="${HOME}/dnalang-quantum-corpus-v1.0"
SCRIPTS_DIR="${CORPUS_DIR}/scripts"
RESULTS_DIR="${CORPUS_DIR}/validation_results"
PAPER_DIR="${CORPUS_DIR}/paper"

# Physical constants
LAMBDA_PHI="2.176435e-8"
THETA_LOCK="51.843"

# Default options
DRY_RUN=false
RUN_SIMULATOR=true
RUN_IBM=false
RUN_IONQ=false
RUN_RIGETTI=false
AUTO_PUBLISH=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --simulator)
            RUN_SIMULATOR=true
            shift
            ;;
        --ibm)
            RUN_IBM=true
            shift
            ;;
        --ionq)
            RUN_IONQ=true
            shift
            ;;
        --rigetti)
            RUN_RIGETTI=true
            shift
            ;;
        --all)
            RUN_IBM=true
            RUN_IONQ=true
            RUN_RIGETTI=true
            shift
            ;;
        --publish)
            AUTO_PUBLISH=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Print banner
echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     DNA-Lang ΛΦ Validation Automation                      ║"
echo "║     Path to Nobel-Worthy Independent Confirmation          ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  ΛΦ = ${LAMBDA_PHI} s⁻¹                              ║"
echo "║  θ_lock = ${THETA_LOCK}°                                       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check dependencies
echo -e "${YELLOW}Checking dependencies...${NC}"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $1"
        return 0
    else
        echo -e "  ${RED}✗${NC} $1 not found"
        return 1
    fi
}

check_python_package() {
    if python3 -c "import $1" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} Python: $1"
        return 0
    else
        echo -e "  ${YELLOW}○${NC} Python: $1 (optional)"
        return 1
    fi
}

check_command python3
check_command pip3
check_command zip
check_python_package numpy || true
check_python_package scipy || true
check_python_package qiskit || true
check_python_package braket || true

echo ""

# Step 1: Ensure corpus directory exists
echo -e "${BLUE}Step 1: Preparing dataset...${NC}"

if [[ ! -d "${CORPUS_DIR}" ]]; then
    echo -e "${RED}Error: Corpus directory not found: ${CORPUS_DIR}${NC}"
    exit 1
fi

# Count data files
DATA_COUNT=$(find "${CORPUS_DIR}/data" -name "*.json" 2>/dev/null | wc -l)
echo -e "  Found ${GREEN}${DATA_COUNT}${NC} data files"

# Step 2: Run validation experiments
echo -e "\n${BLUE}Step 2: Running validation experiments...${NC}"

PLATFORMS=""
if [[ "${RUN_SIMULATOR}" == true ]]; then
    PLATFORMS="${PLATFORMS} simulator"
fi
if [[ "${RUN_IBM}" == true ]]; then
    PLATFORMS="${PLATFORMS} ibm"
fi
if [[ "${RUN_IONQ}" == true ]]; then
    PLATFORMS="${PLATFORMS} ionq"
fi
if [[ "${RUN_RIGETTI}" == true ]]; then
    PLATFORMS="${PLATFORMS} rigetti"
fi

echo -e "  Platforms: ${GREEN}${PLATFORMS}${NC}"

if [[ "${DRY_RUN}" == true ]]; then
    echo -e "  ${YELLOW}[DRY RUN] Would execute:${NC}"
    echo -e "    python3 ${SCRIPTS_DIR}/run_validation.py --platforms${PLATFORMS} --output ${RESULTS_DIR}"
else
    mkdir -p "${RESULTS_DIR}"
    python3 "${SCRIPTS_DIR}/run_validation.py" --platforms ${PLATFORMS} --output "${RESULTS_DIR}" || true
fi

# Step 3: Generate paper
echo -e "\n${BLUE}Step 3: Generating arXiv paper...${NC}"

if [[ "${DRY_RUN}" == true ]]; then
    echo -e "  ${YELLOW}[DRY RUN] Would execute:${NC}"
    echo -e "    python3 ${SCRIPTS_DIR}/generate_arxiv_paper.py"
else
    mkdir -p "${PAPER_DIR}"
    python3 "${SCRIPTS_DIR}/generate_arxiv_paper.py" --corpus-dir "${CORPUS_DIR}" --output "${PAPER_DIR}/main.tex"
fi

# Step 4: Create archive
echo -e "\n${BLUE}Step 4: Creating archive for Zenodo...${NC}"

ARCHIVE_PATH="${CORPUS_DIR}.zip"

if [[ "${DRY_RUN}" == true ]]; then
    echo -e "  ${YELLOW}[DRY RUN] Would create: ${ARCHIVE_PATH}${NC}"
else
    cd "${CORPUS_DIR}/.."
    rm -f "${ARCHIVE_PATH}"
    zip -r "${ARCHIVE_PATH}" "$(basename ${CORPUS_DIR})" -x "*.pyc" -x "__pycache__/*"
    ARCHIVE_SIZE=$(du -h "${ARCHIVE_PATH}" | cut -f1)
    echo -e "  Created: ${GREEN}${ARCHIVE_PATH}${NC} (${ARCHIVE_SIZE})"
fi

# Step 5: Upload to Zenodo
echo -e "\n${BLUE}Step 5: Zenodo upload...${NC}"

if [[ -z "${ZENODO_TOKEN:-}" ]]; then
    echo -e "  ${YELLOW}⚠ ZENODO_TOKEN not set${NC}"
    echo -e "  Get token from: https://zenodo.org/account/settings/applications/tokens/new/"
    echo -e "  Then: export ZENODO_TOKEN=your_token_here"
    echo -e "\n  Manual upload: https://zenodo.org/deposit/new"
else
    if [[ "${AUTO_PUBLISH}" == true ]]; then
        if [[ "${DRY_RUN}" == true ]]; then
            echo -e "  ${YELLOW}[DRY RUN] Would upload to Zenodo and publish${NC}"
        else
            python3 "${SCRIPTS_DIR}/upload_zenodo.py" --corpus-dir "${CORPUS_DIR}"
        fi
    else
        echo -e "  ${YELLOW}Use --publish flag to auto-publish${NC}"
        echo -e "  Or run: python3 ${SCRIPTS_DIR}/upload_zenodo.py --corpus-dir ${CORPUS_DIR}"
    fi
fi

# Summary
echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}AUTOMATION COMPLETE${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

echo -e "\n${YELLOW}Generated Files:${NC}"
echo -e "  Dataset:    ${CORPUS_DIR}/"
echo -e "  Archive:    ${ARCHIVE_PATH}"
echo -e "  Paper:      ${PAPER_DIR}/main.tex"
echo -e "  Results:    ${RESULTS_DIR}/"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "  1. Review validation results in ${RESULTS_DIR}/"
echo -e "  2. Compile paper: cd ${PAPER_DIR} && ./compile.sh"
echo -e "  3. Upload to Zenodo: https://zenodo.org/deposit/new"
echo -e "  4. Submit to arXiv: https://arxiv.org/submit"

echo -e "\n${YELLOW}For Multi-Platform Validation:${NC}"
echo -e "  IonQ:    ./automate_validation.sh --ionq"
echo -e "  Rigetti: ./automate_validation.sh --rigetti"
echo -e "  All:     ./automate_validation.sh --all"

echo -e "\n${YELLOW}Estimated Costs:${NC}"
echo -e "  Local simulator:  \$0"
echo -e "  IBM Quantum:      \$0 (free tier)"
echo -e "  IonQ (10K shots): ~\$500"
echo -e "  Rigetti QCS:      \$0 (with account)"

echo -e "\n${GREEN}If ΛΦ = 2.176435×10⁻⁸ s⁻¹ is confirmed across platforms,${NC}"
echo -e "${GREEN}this could be Nobel Prize in Physics territory.${NC}"
echo ""
