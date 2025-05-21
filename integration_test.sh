#!/bin/bash
#
# ─────────────────────────────────────────────────────────────────────
#  CRYPTO ANALYST AGENT SWARM - INTEGRATION TEST SCRIPT
# ─────────────────────────────────────────────────────────────────────
#  This script runs the complete Crypto Analyst Agent Swarm pipeline:
#  1. Refresh indicators from external sources
#  2. Run all agents to analyze the data
#  3. Aggregate agent votes into a consensus
#  4. Apply risk management overrides
#  5. Generate a daily market brief
#
#  Usage:
#    bash integration_test.sh [DATE]
#    
#    DATE: Optional date in YYYY-MM-DD format (default: today)
#
#  Prerequisites:
#    1. Run scripts/generate_mock_data.py
#    2. Run scripts/generate_mock_outputs.py
# ─────────────────────────────────────────────────────────────────────

set -e  # Exit on error

# Directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${SCRIPT_DIR}/data"
LOGS_DIR="${DATA_DIR}/logs"
AGENT_SPECS_DIR="${DATA_DIR}/agents"

# Date handling
if [ -z "$1" ]; then
  # Use today's date if not specified
  DATE=$(date +%Y-%m-%d)
else
  DATE=$1
fi

echo "============================================================="
echo "CRYPTO ANALYST AGENT SWARM - INTEGRATION TEST"
echo "Date: ${DATE}"
echo "============================================================="

# Create necessary directories
mkdir -p "${LOGS_DIR}"
mkdir -p "${DATA_DIR}/indicators"
mkdir -p "${DATA_DIR}/outputs"
mkdir -p "${DATA_DIR}/consensus"
mkdir -p "${DATA_DIR}/briefs"

# Log file
LOG_FILE="${LOGS_DIR}/integration_test_${DATE}.log"
echo "Starting integration test for date ${DATE}" > "${LOG_FILE}"
echo "Timestamp: $(date)" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

# Function to run and log a command
run_command() {
  local cmd=$1
  local step_name=$2
  
  echo ""
  echo "-------------------------------------------------------------"
  echo "STEP: ${step_name}"
  echo "COMMAND: ${cmd}"
  echo "-------------------------------------------------------------"
  
  echo "STEP: ${step_name}" >> "${LOG_FILE}"
  echo "COMMAND: ${cmd}" >> "${LOG_FILE}"
  echo "" >> "${LOG_FILE}"
  
  # Run the command and tee output to both console and log file
  eval "${cmd}" 2>&1 | tee -a "${LOG_FILE}"
  
  # Capture the exit status
  local status=${PIPESTATUS[0]}
  if [ $status -ne 0 ]; then
    echo "ERROR: Command failed with status $status" | tee -a "${LOG_FILE}"
    echo "Continuing with next step..." | tee -a "${LOG_FILE}"
  fi
  
  echo "" >> "${LOG_FILE}"
}

# 1. Verify mock indicator data exists
echo "Step 1: Verifying mock indicators for ${DATE}..."
MOCK_INDICATOR_PATH="${DATA_DIR}/indicators/cbbi/${DATE}.json"
if [ -f "${MOCK_INDICATOR_PATH}" ]; then
  echo "✅ Mock indicator data found for ${DATE}"
else
  echo "❌ No mock indicator data found at ${MOCK_INDICATOR_PATH}"
  echo "Please run: python3 ${SCRIPT_DIR}/scripts/generate_mock_data.py --date ${DATE}"
  exit 1
fi

# 2. Verify mock agent outputs exist
echo "Step 2: Verifying mock agent outputs for ${DATE}..."
MOCK_AGENT_OUTPUT_PATH="${DATA_DIR}/outputs/the_trader/${DATE}.json"
if [ -f "${MOCK_AGENT_OUTPUT_PATH}" ]; then
  echo "✅ Mock agent outputs found for ${DATE}"
else
  echo "❌ No mock agent outputs found at ${MOCK_AGENT_OUTPUT_PATH}"
  echo "Please run: python3 ${SCRIPT_DIR}/scripts/generate_mock_outputs.py --date ${DATE}"
  exit 1
fi

# 3. Aggregate votes
echo "Step 3: Aggregating agent votes for ${DATE}..."
run_command "python3 ${SCRIPT_DIR}/scripts/aggregate_votes.py --date ${DATE}" "Aggregate Votes"

# 4. Apply risk engine
echo "Step 4: Applying risk management overrides for ${DATE}..."
run_command "python3 ${SCRIPT_DIR}/scripts/risk_engine.py --date ${DATE}" "Risk Engine"

# 5. Generate daily brief
echo "Step 5: Generating daily brief for ${DATE}..."
BRIEF_PATH="${DATA_DIR}/briefs/${DATE}.md"
run_command "python3 ${SCRIPT_DIR}/scripts/generate_daily_brief.py --date ${DATE} --output file" "Generate Daily Brief"

# Print final summary
echo ""
echo "============================================================="
echo "INTEGRATION TEST COMPLETE"
echo "Date: ${DATE}"
echo "Log: ${LOG_FILE}"
echo "Brief: ${BRIEF_PATH}"
echo "============================================================="

# Check if the brief was generated successfully
if [ -f "${BRIEF_PATH}" ]; then
  echo "Brief generated successfully at ${BRIEF_PATH}"
  echo ""
  echo "Preview of the brief:"
  echo "-------------------------------------------------------------"
  head -n 20 "${BRIEF_PATH}"
  echo "..."
  echo "-------------------------------------------------------------"
  echo "To view the full brief, run: cat ${BRIEF_PATH}"
else
  echo "WARNING: Brief file was not generated at expected location: ${BRIEF_PATH}"
fi

echo ""
echo "To post this brief to Discord (not run in test mode), you would run:"
echo "python3 ${SCRIPT_DIR}/scripts/post_to_discord.py --date ${DATE}"
