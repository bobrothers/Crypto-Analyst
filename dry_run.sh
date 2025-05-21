#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
#  CRYPTO ANALYST AGENT SWARM – DRY RUN TESTING GUIDE
# ───────────────────────────────────────────────────────────────────────────
#  This script demonstrates how to test each component of the agent swarm
#  individually before attempting a full workflow execution.
# ───────────────────────────────────────────────────────────────────────────

# 1) Load environment variables from .env file
# This makes all API keys and configuration accessible to the scripts
echo "Loading environment variables..."
source .env

# 2) Refresh market indicators (with dry-run flag to avoid API calls)
# This will use sample data or generate placeholders instead of calling real APIs
echo "Testing indicator refresh..."
python scripts/refresh_indicators.py --date 2025-05-20 --no-save --output json

# 3) Run a single agent to test its analysis capabilities
# Start with The Trader as it has well-defined outputs
echo "Testing individual agent analysis..."
python agents/run_agent.py --name "The Trader" --date 2025-05-20 --output json

# 4) Test vote aggregation with existing agent outputs
# This will combine individual agent analyses into a consensus
echo "Testing vote aggregation..."
python scripts/aggregate_votes.py --date 2025-05-20 --output json

# 5) Generate a daily brief from the consensus and indicators
# This will create a markdown report using the Jinja2 template
echo "Testing brief generation..."
python scripts/generate_daily_brief.py --date 2025-05-20 --output stdout

# 6) Test Discord posting (use a test channel for initial tests)
# Replace the channel ID with a test channel to avoid posting to production
echo "Testing Discord posting (to test channel)..."
python scripts/post_to_discord.py --channel_id="TEST_CHANNEL_ID" --file data/briefs/daily_brief_2025-05-20.md

# 7) Full workflow dry-run
# Once individual components work, test the full sequence
echo "Testing complete workflow sequence..."
echo "1. Refresh indicators..."
python scripts/refresh_indicators.py --date 2025-05-20

echo "2. Run all agents..."
for agent in "The Crypto Believer" "The Trader" "Sentiment Maxi" "Financial Nihilist" "Risk Agent" "SOL Maxi" "ETH Maxi" "BTC Maxi"
do
  echo "  - Running $agent..."
  python agents/run_agent.py --name "$agent" --date 2025-05-20
done

echo "3. Aggregate votes..."
python scripts/aggregate_votes.py --date 2025-05-20

echo "4. Generate brief..."
python scripts/generate_daily_brief.py --date 2025-05-20

echo "5. Post to Discord (test channel)..."
python scripts/post_to_discord.py --channel_id="TEST_CHANNEL_ID" --file data/briefs/daily_brief_2025-05-20.md

echo "Dry run complete!"
