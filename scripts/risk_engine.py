#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
risk_engine.py
-------------
Risk management engine for the Crypto Analyst Agent Swarm.
Applies risk management overrides to consensus recommendations
based on critical indicator values.
"""

import os
import json
import yaml
import logging
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('risk_engine')

# Define paths
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data')
INDICATORS_DIR = os.path.join(DATA_DIR, 'indicators')
CONSENSUS_DIR = os.path.join(DATA_DIR, 'consensus')
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
ACTION_MAP_PATH = os.path.join(CONFIG_DIR, 'action_map.yaml')


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
        return {}


def load_consensus(date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load consensus data for a specific date.
    
    Args:
        date: Date string in YYYY-MM-DD format
        
    Returns:
        Consensus data dictionary or None if not found
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    filepath = os.path.join(CONSENSUS_DIR, f"{date_str}.json")
    
    if not os.path.exists(filepath):
        logger.error(f"Consensus file not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r') as f:
            consensus = json.load(f)
        logger.info(f"Loaded consensus from {filepath}")
        return consensus
    except Exception as e:
        logger.error(f"Failed to load consensus from {filepath}: {str(e)}")
        return None


def load_indicator(indicator_name: str, date: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load indicator data for a specific date.
    
    Args:
        indicator_name: Name of the indicator
        date: Date string in YYYY-MM-DD format
    
    Returns:
        Indicator data dictionary or None if not found
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    normalized_name = indicator_name.lower().replace(' ', '_')
    filepath = os.path.join(INDICATORS_DIR, normalized_name, f"{date_str}.json")
    
    if not os.path.exists(filepath):
        logger.error(f"Indicator file not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r') as f:
            indicator = json.load(f)
        logger.info(f"Loaded indicator {indicator_name} from {filepath}")
        return indicator
    except Exception as e:
        logger.error(f"Failed to load indicator from {filepath}: {str(e)}")
        return None


def load_indicators(date: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """
    Load all indicators for a specific date.
    
    Args:
        date: Date string in YYYY-MM-DD format
    
    Returns:
        Dictionary mapping indicator names to their data
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    indicators = {}
    
    # Get all indicator directories
    indicator_dirs = [d for d in os.listdir(INDICATORS_DIR) 
                     if os.path.isdir(os.path.join(INDICATORS_DIR, d))]
    
    for dir_name in indicator_dirs:
        # Convert directory name to display name
        display_name = dir_name.replace('_', ' ').title()
        
        # Load indicator
        indicator = load_indicator(display_name, date_str)
        if indicator:
            indicators[display_name] = indicator
    
    logger.info(f"Loaded {len(indicators)} indicators for date {date_str}")
    return indicators


def check_cbbi_risk(indicator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if CBBI indicator is in a high risk zone.
    
    Args:
        indicator: CBBI indicator data
    
    Returns:
        Risk flag dictionary or None if no risk
    """
    if 'value' not in indicator:
        return None
    
    cbbi_value = indicator['value']
    
    # CBBI >= 0.8 is high risk
    if cbbi_value >= 0.8:
        return {
            'flag': 'cbbi_high',
            'value': cbbi_value,
            'threshold': 0.8,
            'name': 'High CBBI',
            'description': f"CBBI value of {cbbi_value:.2f} indicates extreme market euphoria",
            'emoji': '⚠️'
        }
    
    return None


def check_rainbow_risk(indicator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if Rainbow band indicator is in a high risk zone.
    
    Args:
        indicator: Rainbow bands indicator data
    
    Returns:
        Risk flag dictionary or None if no risk
    """
    if 'value' not in indicator:
        return None
    
    band_value = indicator['value']
    
    # Band >= 7 is high risk (top bands)
    if band_value >= 7:
        return {
            'flag': 'rainbow_top',
            'value': band_value,
            'threshold': 7,
            'name': 'Top Rainbow Band',
            'description': f"BTC price is in band {band_value} of the Rainbow Chart, indicating potential top",
            'emoji': '🌈'
        }
    
    return None


def check_pi_cycle_risk(indicator: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Check if Pi-Cycle indicator is near a market top.
    
    Args:
        indicator: Pi-Cycle indicator data
    
    Returns:
        Risk flag dictionary or None if no risk
    """
    if 'value' not in indicator:
        return None
    
    pi_value = indicator['value']
    
    # Pi-Cycle >= 0.95 is high risk
    if pi_value >= 0.95:
        return {
            'flag': 'pi_cycle_top',
            'value': pi_value,
            'threshold': 0.95,
            'name': 'Pi-Cycle Near Top',
            'description': f"Pi-Cycle value of {pi_value:.2f} indicates potential market top",
            'emoji': 'π'
        }
    
    return None


def apply_risk_overrides(consensus: Dict[str, Any], indicators: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Apply risk management overrides to consensus recommendations.
    
    Args:
        consensus: Consensus data dictionary
        indicators: Dictionary mapping indicator names to their data
    
    Returns:
        Updated consensus dictionary with risk flags
    """
    risk_flags = []
    forced_action = None
    
    # Check CBBI risk
    if 'Cbbi' in indicators:
        cbbi_risk = check_cbbi_risk(indicators['Cbbi'])
        if cbbi_risk:
            risk_flags.append(cbbi_risk)
            forced_action = 'de-risk'
            logger.info(f"Risk flag triggered: {cbbi_risk['name']}")
    
    # Check Rainbow Bands risk
    if 'Rainbow Bands' in indicators:
        rainbow_risk = check_rainbow_risk(indicators['Rainbow Bands'])
        if rainbow_risk:
            risk_flags.append(rainbow_risk)
            forced_action = 'de-risk'
            logger.info(f"Risk flag triggered: {rainbow_risk['name']}")
    
    # Check Pi-Cycle risk
    if 'Pi Cycle' in indicators:
        pi_risk = check_pi_cycle_risk(indicators['Pi Cycle'])
        if pi_risk:
            risk_flags.append(pi_risk)
            forced_action = 'de-risk'
            logger.info(f"Risk flag triggered: {pi_risk['name']}")
    
    # Create a copy of the consensus to modify
    updated_consensus = consensus.copy()
    
    # Add risk flags to the consensus
    updated_consensus['risk_flags'] = risk_flags
    
    # Override action if needed
    if forced_action and risk_flags:
        # Load action map to get emoji
        config = load_config(ACTION_MAP_PATH)
        action_mapping = next((mapping for mapping in config.get('consensus_to_action', []) 
                              if mapping.get('action') == forced_action), {})
        
        previous_action = updated_consensus.get('action', 'hold')
        updated_consensus['original_action'] = previous_action
        updated_consensus['action'] = forced_action
        updated_consensus['emoji'] = action_mapping.get('emoji', '🔴')
        updated_consensus['risk_override'] = True
        
        logger.info(f"Action overridden from '{previous_action}' to '{forced_action}' due to risk flags")
    else:
        updated_consensus['risk_override'] = False
    
    return updated_consensus


def save_consensus(consensus: Dict[str, Any], date: Optional[str] = None) -> str:
    """
    Save the updated consensus results to a file.
    
    Args:
        consensus: The consensus dictionary to save
        date: Optional date string (YYYY-MM-DD)
    
    Returns:
        Path to the saved consensus file
    """
    date_str = date or datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}.json"
    filepath = os.path.join(CONSENSUS_DIR, filename)
    
    with open(filepath, 'w') as f:
        json.dump(consensus, f, indent=2)
    
    logger.info(f"Saved updated consensus to {filepath}")
    return filepath


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Apply risk management overrides to consensus')
    parser.add_argument('--date', help='Date to process (YYYY-MM-DD)')
    parser.add_argument('--output', choices=['json', 'path', 'none'], default='none',
                        help='Output format (default: none)')
    args = parser.parse_args()
    
    try:
        date_str = args.date or datetime.now().strftime('%Y-%m-%d')
        
        # Load consensus
        consensus = load_consensus(date_str)
        if not consensus:
            logger.error(f"No consensus found for date {date_str}")
            return 1
        
        # Load indicators
        indicators = load_indicators(date_str)
        if not indicators:
            logger.error(f"No indicators found for date {date_str}")
            return 1
        
        # Apply risk overrides
        updated_consensus = apply_risk_overrides(consensus, indicators)
        
        # Save updated consensus
        output_path = save_consensus(updated_consensus, date_str)
        
        # Handle output format
        if args.output == 'json':
            print(json.dumps(updated_consensus, indent=2))
        elif args.output == 'path':
            print(output_path)
        
        return 0
    except Exception as e:
        logger.error(f"Error during risk analysis: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
