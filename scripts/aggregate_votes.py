#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aggregate_votes.py
-----------------
Aggregates the outputs from all agents in the Crypto Analyst Agent Swarm
to produce a single consensus view and recommended action.

This script is called after all agents have completed their individual analyses
in the daily_swarm_workflow defined in swarm.yaml.
"""

import os
import json
import logging
import argparse
import glob
import yaml
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('aggregate_votes')

# Define paths
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data')
AGENT_OUTPUT_DIR = os.path.join(DATA_DIR, 'outputs')
CONSENSUS_OUTPUT_DIR = os.path.join(DATA_DIR, 'consensus')
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
ACTION_MAP_PATH = os.path.join(CONFIG_DIR, 'action_map.yaml')


def setup_directories() -> None:
    """Ensure all required directories exist."""
    os.makedirs(AGENT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(CONSENSUS_OUTPUT_DIR, exist_ok=True)
    logger.info("Ensured required directories exist")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load configuration from {config_path}: {str(e)}")
        # Return default configuration
        return {
            'consensus_to_action': [
                {'max': 40, 'action': 'de-risk', 'emoji': '🔴'},
                {'min': 40, 'max': 60, 'action': 'hold', 'emoji': '🟡'},
                {'min': 60, 'action': 'buy', 'emoji': '🟢'}
            ]
        }


def load_agent_outputs(date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load all agent outputs for the specified date.
    
    Args:
        date: Date to load outputs for (YYYY-MM-DD format)
              If None, use the latest available outputs
    
    Returns:
        List of agent output dictionaries
    """
    agent_outputs = []
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    
    # Iterate through each agent directory
    for agent_dir in os.listdir(AGENT_OUTPUT_DIR):
        agent_path = os.path.join(AGENT_OUTPUT_DIR, agent_dir)
        if os.path.isdir(agent_path):
            # Look for the output file with the given date
            output_file = os.path.join(agent_path, f"{date_str}.json")
            if os.path.exists(output_file):
                try:
                    with open(output_file, 'r') as f:
                        data = json.load(f)
                        agent_outputs.append(data)
                        logger.info(f"Loaded agent output: {agent_dir}/{date_str}.json")
                except Exception as e:
                    logger.error(f"Failed to load {output_file}: {str(e)}")
    
    if not agent_outputs:
        logger.warning(f"No agent outputs found for date: {date_str}")
    
    return agent_outputs


def calculate_consensus_pct(agent_outputs: List[Dict[str, Any]]) -> float:
    """
    Calculate consensus percentage from all agent outputs.
    
    Args:
        agent_outputs: List of agent output dictionaries
    
    Returns:
        Consensus percentage (0-100)
    """
    if not agent_outputs:
        logger.warning("No agent outputs to calculate consensus from")
        return 50.0  # Neutral default
    
    total_score = sum(output.get('score', 50) for output in agent_outputs)
    consensus_pct = (total_score / len(agent_outputs))
    
    logger.info(f"Calculated consensus percentage: {consensus_pct:.2f}")
    return consensus_pct


def map_consensus_to_action(consensus_pct: float, action_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map consensus percentage to a recommended action.
    
    Args:
        consensus_pct: The consensus percentage (0-100)
        action_map: The action mapping configuration
    
    Returns:
        Dictionary with action and emoji
    """
    consensus_map = action_map.get('consensus_to_action', [])
    
    for mapping in consensus_map:
        # Check if value is below max threshold
        if 'max' in mapping and consensus_pct < mapping['max']:
            return {
                'action': mapping.get('action', 'hold'),
                'emoji': mapping.get('emoji', '🟡')
            }
        # Check if value is above min threshold and below max threshold
        elif ('min' in mapping and consensus_pct >= mapping['min']) and \
             ('max' in mapping and consensus_pct < mapping['max']):
            return {
                'action': mapping.get('action', 'hold'),
                'emoji': mapping.get('emoji', '🟡')
            }
        # Check if value is above min threshold (no max threshold)
        elif 'min' in mapping and consensus_pct >= mapping['min'] and 'max' not in mapping:
            return {
                'action': mapping.get('action', 'hold'),
                'emoji': mapping.get('emoji', '🟡')
            }
    
    # Default to hold if no mapping matches
    logger.warning(f"No action mapping found for consensus percentage {consensus_pct}, defaulting to hold")
    return {'action': 'hold', 'emoji': '🟡'}


def analyze_agent_distribution(agent_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze the distribution of agent votes.
    
    Args:
        agent_outputs: List of agent output dictionaries
    
    Returns:
        Dictionary with distribution metrics
    """
    if len(agent_outputs) <= 1:
        return {'distribution': {}, 'agreement_level': 1.0}
    
    # Count votes by action
    action_counts = {}
    for output in agent_outputs:
        action = output.get('action', 'HOLD')
        action_counts[action] = action_counts.get(action, 0) + 1
    
    # Calculate agreement level (percentage of agents with the same action)
    max_count = max(action_counts.values()) if action_counts else 0
    agreement_level = max_count / len(agent_outputs) if len(agent_outputs) > 0 else 1.0
    
    return {
        'distribution': action_counts,
        'agreement_level': agreement_level,
        'majority_action': max(action_counts.items(), key=lambda x: x[1])[0] if action_counts else 'HOLD'
    }


def aggregate_votes(agent_outputs: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aggregate votes from all agents to form a consensus.
    
    Args:
        agent_outputs: List of agent output dictionaries
        config: Configuration dictionary
    
    Returns:
        Dictionary with consensus results
    """
    consensus_pct = calculate_consensus_pct(agent_outputs)
    action_mapping = map_consensus_to_action(consensus_pct, config)
    distribution = analyze_agent_distribution(agent_outputs)
    
    # Create agent votes summary
    agent_votes = []
    for output in agent_outputs:
        agent_name = output.get('agent_name', 'Unknown')
        score = output.get('score', 50)
        action = output.get('action', 'HOLD')
        confidence = output.get('confidence', 0.5)
        rationale = output.get('rationale', '')
        
        agent_votes.append({
            'name': agent_name,
            'score': score,
            'action': action,
            'confidence': confidence,
            'rationale': rationale
        })
    
    # Build consensus object
    consensus = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'timestamp': datetime.now().isoformat(),
        'score': consensus_pct,
        'action': action_mapping['action'],
        'emoji': action_mapping['emoji'],
        'agent_votes': agent_votes,
        'distribution': distribution
    }
    
    logger.info(f"Generated consensus with score {consensus_pct:.2f} and action {action_mapping['action']}")
    return consensus


def save_consensus(consensus: Dict[str, Any], date: Optional[str] = None) -> str:
    """
    Save the consensus results to a file.
    
    Args:
        consensus: The consensus dictionary to save
        date: Optional date string (YYYY-MM-DD)
    
    Returns:
        Path to the saved consensus file
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}.json"
    filepath = os.path.join(CONSENSUS_OUTPUT_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(consensus, f, indent=2)
    
    logger.info(f"Saved consensus to {filepath}")
    return filepath


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Aggregate agent votes into consensus')
    parser.add_argument('--date', help='Date to process (YYYY-MM-DD)')
    parser.add_argument('--output', choices=['json', 'path', 'none'], default='none',
                       help='Output format (default: none)')
    args = parser.parse_args()
    
    try:
        setup_directories()
        
        # Load configuration
        config = load_config(ACTION_MAP_PATH)
        
        # Load agent outputs
        agent_outputs = load_agent_outputs(args.date)
        if not agent_outputs:
            logger.error("No agent outputs found, cannot generate consensus")
            return 1
        
        # Calculate consensus
        consensus = aggregate_votes(agent_outputs, config)
        
        # Save results
        output_path = save_consensus(consensus, args.date)
        
        # Handle output format
        if args.output == 'json':
            print(json.dumps(consensus, indent=2))
        elif args.output == 'path':
            print(output_path)
        
        return 0
    except Exception as e:
        logger.error(f"Error during vote aggregation: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
