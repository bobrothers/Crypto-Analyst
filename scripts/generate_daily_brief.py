#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_daily_brief.py
----------------------
Generates a formatted daily briefing based on agent consensus and key indicators.
Uses Jinja2 templates to create a markdown document suitable for Discord posting.

This script is called after the Risk Engine has processed the aggregated agent data
in the daily_swarm_workflow defined in swarm.yaml.
"""

import os
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('generate_daily_brief')

# Define paths
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data')
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
CONSENSUS_DIR = os.path.join(DATA_DIR, 'consensus')
INDICATORS_DIR = os.path.join(DATA_DIR, 'indicators')
OUTPUT_DIR = os.path.join(DATA_DIR, 'briefs')


def setup_directories() -> None:
    """Ensure all required directories exist."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMPLATE_DIR, exist_ok=True)
    logger.info("Ensured required directories exist")


def load_consensus(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Load the consensus data for the specified date.
    
    Args:
        date: Date to load data for (YYYY-MM-DD)
              If None, use the latest available consensus
    
    Returns:
        Consensus data dictionary
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}.json"
    filepath = os.path.join(CONSENSUS_DIR, filename)
    
    try:
        with open(filepath, 'r') as f:
            consensus = json.load(f)
            logger.info(f"Loaded consensus from {filepath}")
            return consensus
    except FileNotFoundError:
        logger.error(f"Consensus file not found: {filepath}")
        raise


def load_indicators(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Load indicator data for the specified date.
    
    Args:
        date: Date to load data for (YYYY-MM-DD)
              If None, use the latest available data
    
    Returns:
        Dictionary of indicator data
    """
    indicators = {}
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    
    # List of key indicators to include in the brief
    key_indicators = [
        'CBBI',
        'Rainbow Bands',
        'Pi Cycle'
    ]
    
    # Load each indicator from its directory
    for indicator_name in key_indicators:
        indicator_dir = os.path.join(INDICATORS_DIR, indicator_name.lower().replace(' ', '_'))
        if not os.path.exists(indicator_dir):
            logger.warning(f"Indicator directory not found: {indicator_dir}")
            continue
            
        indicator_file = os.path.join(indicator_dir, f"{date_str}.json")
        if not os.path.exists(indicator_file):
            logger.warning(f"Indicator file not found: {indicator_file}")
            continue
            
        try:
            with open(indicator_file, 'r') as f:
                data = json.load(f)
                indicators[indicator_name] = data
                logger.info(f"Loaded {indicator_name} indicator from {indicator_file}")
        except Exception as e:
            logger.warning(f"Error loading indicator {indicator_name}: {str(e)}")
    
    logger.info(f"Loaded {len(indicators)} key indicators")
    return indicators


def load_agent_insights(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Load key insights from each agent's output.
    
    Args:
        date: Date to load insights for (YYYY-MM-DD)
    
    Returns:
        Dictionary with agent insights
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    agent_dir = os.path.join(DATA_DIR, 'outputs')
    
    insights = {}
    
    # Check each agent directory for the date file
    for agent_subdir in os.listdir(agent_dir):
        agent_path = os.path.join(agent_dir, agent_subdir)
        if not os.path.isdir(agent_path):
            continue
            
        agent_file = os.path.join(agent_path, f"{date_str}.json")
        if not os.path.exists(agent_file):
            continue
            
        try:
            with open(agent_file, 'r') as f:
                agent_data = json.load(f)
                agent_name = agent_data.get('agent_name', agent_subdir)
                
                insights[agent_name] = {
                    'score': agent_data.get('score', 50),
                    'action': agent_data.get('action', 'HOLD'),
                    'confidence': agent_data.get('confidence', 0.5),
                    'rationale': agent_data.get('rationale', 'No reasoning provided'),
                }
                
                # Extract weighted signals if available
                if 'weighted_signals' in agent_data:
                    insights[agent_name]['signals'] = agent_data['weighted_signals']
                    
        except Exception as e:
            logger.warning(f"Error loading agent file {agent_file}: {str(e)}")
    
    logger.info(f"Loaded insights from {len(insights)} agents")
    return insights


def create_default_template() -> None:
    """Create a default Jinja2 template for the daily brief if none exists."""
    template_path = os.path.join(TEMPLATE_DIR, 'daily_brief.md.j2')
    
    if os.path.exists(template_path):
        logger.info(f"Template already exists at {template_path}")
        return
    
    default_template = """# Crypto Market Brief - {{ date }}

## Consensus View {{ consensus.emoji }}
**Score:** {{ consensus.score | round(1) }}/100
**Action:** {{ consensus.action | upper }}

{% if consensus.risk_override %}
⚠️ **RISK OVERRIDE ACTIVE:** Original action "{{ consensus.original_action | upper }}" overridden to "{{ consensus.action | upper }}" due to risk flags.
{% endif %}

{% if consensus.distribution.agreement_level < 0.5 %}
⚠️ **Warning:** Significant disagreement detected among agents ({{ (consensus.distribution.agreement_level * 100) | round }}% agreement)
{% endif %}

## Risk Flags
{% if consensus.risk_flags %}
{% for flag in consensus.risk_flags %}
- {{ flag.emoji }} **{{ flag.name }}**: {{ flag.description }} (value: {{ flag.value | round(2) }})
{% endfor %}
{% else %}
No critical risk flags detected.
{% endif %}

## Key Indicators
{% for name, indicator in indicators.items() %}
- **{{ name }}:** {{ indicator.value | round(2) }} (signal: {{ indicator.signal }})
{% endfor %}

## Agent Votes
{% for agent in consensus.agent_votes %}
### {{ agent.name }}
- **Score:** {{ agent.score | round(1) }}/100
- **Action:** {{ agent.action }}
- **Confidence:** {{ (agent.confidence * 100) | round(1) }}%
- **Rationale:** {{ agent.rationale }}
{% endfor %}

## Agent Signal Analysis
{% for agent_name, insight in insights.items() if insight.signals is defined %}
### {{ agent_name }} - Signal Weights
{% for signal_name, signal_data in insight.signals.items() %}
- **{{ signal_name }}**: Base score {{ signal_data.base_score }} × Weight {{ signal_data.weight }} = {{ signal_data.weighted_score | round(1) }}
{% endfor %}
{% endfor %}

*Generated by the Crypto Analyst Agent Swarm on {{ generation_time }}*
"""
    
    os.makedirs(os.path.dirname(template_path), exist_ok=True)
    with open(template_path, 'w') as f:
        f.write(default_template)
    logger.info(f"Created default template at {template_path}")


def generate_brief(consensus: Dict[str, Any], 
                  indicators: Dict[str, Any], 
                  insights: Dict[str, Any],
                  date: Optional[str] = None) -> str:
    """
    Generate the daily brief using the Jinja2 template.
    
    Args:
        consensus: Consensus data
        indicators: Indicator data
        insights: Agent insights
        date: Date for the brief (YYYY-MM-DD)
    
    Returns:
        Path to the generated brief file
    """
    # Ensure default template exists
    create_default_template()
    
    # Set up Jinja environment with safe defaults for undefined values
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    
    # Add custom filters
    def safe_round(value, precision=0):
        """Round a number safely, returning 0 for None or undefined values."""
        try:
            if value is None:
                return 0
            return round(float(value), precision)
        except (TypeError, ValueError):
            return 0
            
    env.filters['safe_round'] = safe_round
    
    # Get the template
    template = env.get_template('daily_brief.md.j2')
    
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    context = {
        'date': date_str,
        'consensus': consensus,
        'indicators': indicators,
        'insights': insights,
        'generation_time': datetime.now().isoformat()
    }
    
    # Render the template
    content = template.render(**context)
    
    # Save the rendered brief
    output_filename = f"{date_str}.md"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    with open(output_path, 'w') as f:
        f.write(content)
    
    logger.info(f"Generated daily brief at {output_path}")
    
    # Also save a copy as latest.md for easy access
    latest_path = os.path.join(OUTPUT_DIR, 'latest.md')
    with open(latest_path, 'w') as f:
        f.write(content)
    
    return output_path


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate daily market brief')
    parser.add_argument('--date', help='Date to generate brief for (YYYY-MM-DD)')
    parser.add_argument('--output', choices=['file', 'stdout', 'both'], default='file',
                       help='Output method (default: file)')
    args = parser.parse_args()
    
    try:
        setup_directories()
        
        date_str = args.date or datetime.now().strftime('%Y-%m-%d')
        
        # Load data
        consensus = load_consensus(date_str)
        indicators = load_indicators(date_str)
        insights = load_agent_insights(date_str)
        
        # Generate brief
        output_path = generate_brief(consensus, indicators, insights, date_str)
        
        # Handle output preference
        if args.output in ['stdout', 'both']:
            with open(output_path, 'r') as f:
                print(f.read())
        
        if args.output in ['file', 'both']:
            print(f"Brief generated at: {output_path}")
        
        return 0
    except Exception as e:
        logger.error(f"Error generating daily brief: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
