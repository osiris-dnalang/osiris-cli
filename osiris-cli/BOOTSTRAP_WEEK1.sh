#!/bin/bash

################################################################################
#                                                                              #
#  OSIRIS NOBEL FRAMEWORK — WEEK 1 BOOTSTRAP                                 #
#                                                                              #
#  This script initializes Week 1 execution environment and guides you        #
#  through the pre-registration process on OSF.                              #
#                                                                              #
#  Usage: bash BOOTSTRAP_WEEK1.sh                                            #
#                                                                              #
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}$1${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo ""
}

print_step() {
  echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
  echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
  echo -e "${RED}✗${NC} $1"
}

check_file() {
  if [ -f "$1" ]; then
    print_step "$1 exists"
    return 0
  else
    print_error "$1 NOT FOUND"
    return 1
  fi
}

# Start
clear
print_header "OSIRIS NOBEL FRAMEWORK — WEEK 1 BOOTSTRAP"

echo "This script will:"
echo "  1. Verify all framework files are present"
echo "  2. Check Python environment"
echo "  3. Test code modules"
echo "  4. Generate execution specifications"
echo "  5. Display next steps for pre-registration"
echo ""

# Step 1: Verify files
print_header "STEP 1: Verifying Framework Files"

required_files=(
  "START_HERE.md"
  "WEEK_1_EXECUTION_CHECKLIST.md"
  "OSF_PRE_REGISTRATION_GUIDE.md"
  "OSIRIS_NOBEL_SUBMISSION.tex"
  "NOBLE_EXECUTION_PLAYBOOK.md"
  "RESEARCH_INTEGRITY.md"
)

all_files_present=true
for file in "${required_files[@]}"; do
  if check_file "$file"; then
    :
  else
    all_files_present=false
  fi
done

echo ""
if [ "$all_files_present" = true ]; then
  print_step "All core documents present"
else
  print_error "Some documents missing - framework incomplete"
  exit 1
fi

# Step 2: Check Python
print_header "STEP 2: Checking Python Environment"

if command -v python3 &> /dev/null; then
  python_version=$(python3 --version)
  print_step "Python found: $python_version"
else
  print_error "Python3 not found"
  exit 1
fi

# Step 3: Test code modules
print_header "STEP 3: Testing Code Modules"

python3 -m py_compile OSIRIS_EXPERIMENTAL_PROTOCOL.py && \
  print_step "OSIRIS_EXPERIMENTAL_PROTOCOL.py syntax OK" || \
  { print_error "Syntax error in OSIRIS_EXPERIMENTAL_PROTOCOL.py"; exit 1; }

python3 -m py_compile OSIRIS_EXOTIC_PHYSICS_TESTS.py && \
  print_step "OSIRIS_EXOTIC_PHYSICS_TESTS.py syntax OK" || \
  { print_error "Syntax error in OSIRIS_EXOTIC_PHYSICS_TESTS.py"; exit 1; }

# Step 4: Generate specs (if not already present)
print_header "STEP 4: Generating Experimental Specifications"

if [ -f "OSIRIS_EXPERIMENTAL_SPEC.json" ]; then
  print_step "OSIRIS_EXPERIMENTAL_SPEC.json already exists"
else
  print_warning "Generating OSIRIS_EXPERIMENTAL_SPEC.json..."
  python3 OSIRIS_EXPERIMENTAL_PROTOCOL.py > /dev/null 2>&1 && \
    print_step "Generated OSIRIS_EXPERIMENTAL_SPEC.json" || \
    { print_error "Failed to generate spec"; exit 1; }
fi

if [ -f "OSIRIS_PHYSICS_TEST_MATRIX.json" ]; then
  print_step "OSIRIS_PHYSICS_TEST_MATRIX.json already exists"
else
  print_warning "Generating OSIRIS_PHYSICS_TEST_MATRIX.json..."
  python3 OSIRIS_EXOTIC_PHYSICS_TESTS.py > /dev/null 2>&1 && \
    print_step "Generated OSIRIS_PHYSICS_TEST_MATRIX.json" || \
    { print_error "Failed to generate tests"; exit 1; }
fi

# Step 5: Display status
print_header "WEEK 1 BOOTSTRAP COMPLETE ✓"

echo ""
echo "✅ Framework Status:"
echo "  • All 6+ core documents present"
echo "  • Python environment ready"
echo "  • Code modules syntax valid"
echo "  • Experimental specs generated"
echo ""

# Step 6: Next actions
print_header "NEXT STEPS — Your Week 1 Roadmap"

echo "📅 TODAY (Time: 2 hours)"
echo "  1. Read START_HERE.md (15 min)"
echo "     → Understand the complete strategy"
echo ""
echo "  2. Read WEEK_1_EXECUTION_CHECKLIST.md (20 min)"
echo "     → See your daily tasks"
echo ""
echo "  3. Read WEEK_1_EXECUTION_SUMMARY.md (15 min)"
echo "     → Understand what's delivered"
echo ""
echo ""
echo "📅 THIS WEEK (Days 1-5, 3.3 hours total execution)"
echo ""
echo "  Day 1 (Monday):"
echo "    → Finish reading framework docs (45 min)"
echo ""
echo "  Day 2 (Tuesday):"
echo "    → Create OSF account at https://osf.io"
echo "    → Create new project + project description"
echo "    → Time: 30 min"
echo ""
echo "  Day 3 (Wednesday):"
echo "    → Upload specs to OSF project"
echo "    → Begin filling pre-registration form"
echo "    → Time: 35 min"
echo ""
echo "  Day 4 (Thursday):"
echo "    → Email external researcher for protocol review"
echo "    → Share OSF project link + pre-registration form draft"
echo "    → Time: 25 min"
echo ""
echo "  Day 5 (Friday) ⭐ CRITICAL:"
echo "    → Incorporate reviewer feedback"
echo "    → LOCK pre-registration publicly on OSF"
echo "    → This creates immutable, timestamped record"
echo "    → Time: 50 min"
echo ""
echo ""
echo "🎯 Week 1 Deliverable:"
echo "   PUBLIC OSF Pre-Registration URL"
echo "   (Example: https://osf.io/abc123/)"
echo ""
echo ""

# Commands to help
print_header "HELPFUL COMMANDS"

echo "View the guides:"
echo "  cat START_HERE.md | less"
echo ""
echo "View your checklist:"
echo "  cat WEEK_1_EXECUTION_CHECKLIST.md | less"
echo ""
echo "View OSF guide:"
echo "  cat OSF_PRE_REGISTRATION_GUIDE.md | less"
echo ""
echo "View the complete playbook:"
echo "  cat NOBLE_EXECUTION_PLAYBOOK.md | less"
echo ""
echo "View research integrity safeguards:"
echo "  cat RESEARCH_INTEGRITY.md | less"
echo ""
echo "View generated specifications:"
echo "  cat OSIRIS_EXPERIMENTAL_SPEC.json | python3 -m json.tool | less"
echo ""

# Final message
print_header "YOU ARE READY"

echo "✅ Framework bootstrapped successfully"
echo "✅ All systems operational"
echo "✅ Specifications generated"
echo "✅ Ready for Week 1 execution"
echo ""
echo "🚀 Next action: Read START_HERE.md (15 minutes)"
echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""

exit 0
