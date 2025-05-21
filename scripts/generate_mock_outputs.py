#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_mock_outputs.py
-----------------------
Generates mock agent outputs for testing the Crypto Analyst Agent Swarm pipeline.
Simulates the outputs of multiple agents analyzing indicator data.
"""

import os
import json
import argparse
import random
from datetime import datetime

# Define paths
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data')
AGENT_SPECS_DIR = os.path.join(DATA_DIR, 'agents')
INDICATORS_DIR = os.path.join(DATA_DIR, 'indicators')
OUTPUTS_DIR = os.path.join(DATA_DIR, 'outputs')


def setup_directories():
    """Ensure all required directories exist."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    

def load_agent_specs():
    """
    Load all agent specifications.
    
    Returns:
        List of agent specification dictionaries
    """
    agents = []
    
    for filename in os.listdir(AGENT_SPECS_DIR):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(AGENT_SPECS_DIR, filename), 'r') as f:
                    agent_spec = json.load(f)
                    # Make sure the agent has a name, use filename if missing
                    if 'name' not in agent_spec:
                        agent_spec['name'] = os.path.splitext(filename)[0]
                    agents.append(agent_spec)
                    print(f"Loaded agent spec: {filename} - {agent_spec['name']}")
            except Exception as e:
                print(f"Error loading {filename}: {str(e)}")
    
    return agents


def load_indicators(date_str):
    """
    Load all indicators for the specified date.
    
    Args:
        date_str: Date string (YYYY-MM-DD)
        
    Returns:
        Dictionary of indicators
    """
    indicators = {}
    
    # List of indicators to load
    indicator_names = ['cbbi', 'rainbow_bands', 'pi_cycle']
    
    for indicator_name in indicator_names:
        try:
            filepath = os.path.join(INDICATORS_DIR, indicator_name, f"{date_str}.json")
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    indicator_data = json.load(f)
                    indicators[indicator_data.get('name', indicator_name.title())] = indicator_data
                    print(f"Loaded indicator: {indicator_name}")
        except Exception as e:
            print(f"Error loading indicator {indicator_name}: {str(e)}")
    
    return indicators


def generate_mock_output(agent_spec, indicators, date_str):
    """
    Generate a mock agent output based on agent spec and indicators.
    
    Args:
        agent_spec: Agent specification dictionary
        indicators: Dictionary of indicators
        date_str: Date string (YYYY-MM-DD)
        
    Returns:
        Generated agent output dictionary
    """
    # Ensure agent name is available, use a fallback if needed
    agent_name = agent_spec.get('name', 'Unknown Agent')
    agent_type = agent_spec.get('type', 'rule_based')
    
    print(f"Generating output for {agent_name}")
    
    # Generate a base score influenced by indicators but with agent biases
    # Start with a neutral score
    base_score = 50
    
    # Apply biases based on agent type and philosophy
    if 'philosophy' in agent_spec:
        philosophy = agent_spec['philosophy'].lower()
        # Bullish bias
        if 'bull' in philosophy or 'optimist' in philosophy:
            base_score += random.randint(5, 15)
        # Bearish bias
        elif 'bear' in philosophy or 'pessimist' in philosophy or 'nihilist' in philosophy:
            base_score -= random.randint(5, 15)
    
    # Influence score based on indicators
    for indicator_name, indicator in indicators.items():
        signal = indicator.get('signal', 'neutral')
        
        signal_impact = 0
        if signal == 'bullish':
            signal_impact = random.randint(5, 10)
        elif signal == 'bearish':
            signal_impact = -random.randint(5, 10)
            
        # Apply different weights based on the agent's preferences
        if 'BTC Maxi' in agent_name and indicator_name == 'Rainbow Bands':
            signal_impact *= 1.5
        elif 'Risk Agent' in agent_name and indicator_name == 'CBBI':
            signal_impact *= 2
            
        base_score += signal_impact
    
    # Ensure score is within 0-100 range
    score = max(0, min(100, base_score))
    
    # Determine action based on score
    action = 'HOLD'
    if score >= 75:
        action = 'STRONG_BUY'
    elif score >= 60:
        action = 'BUY'
    elif score <= 25:
        action = 'STRONG_SELL'
    elif score <= 40:
        action = 'SELL'
    
    # Generate confidence level (higher near extremes)
    distance_from_center = abs(score - 50) / 50  # 0 at center, 1 at extremes
    confidence = 0.5 + (distance_from_center * 0.4) + random.uniform(-0.1, 0.1)
    confidence = max(0.3, min(0.95, confidence))
    
    # Create a custom rationale based on agent type and indicators
    rationales = [
        f"Based on current indicators, I am {action.lower().replace('_', ' ')} on the market.",
        f"My analysis shows a score of {score:.1f}, indicating a {action.lower().replace('_', ' ')} stance.",
        f"The combination of {', '.join(indicators.keys())} suggests a {action.lower().replace('_', ' ')} position.",
        f"Market conditions indicate a {score:.1f}% bullish sentiment, leading to a {action.lower().replace('_', ' ')} recommendation."
    ]
    
    rationale = random.choice(rationales)
    
    # Generate weighted signals based on indicator values
    weighted_signals = {}
    weights = agent_spec.get('weights', {})
    
    for indicator_name, indicator in indicators.items():
        if indicator_name in weights:
            weight = weights.get(indicator_name, 0.33)
            signal = indicator.get('signal', 'neutral')
            
            # Convert signal to base score
            base_score = 50  # neutral default
            if signal == 'bullish':
                base_score = 75
            elif signal == 'bearish':
                base_score = 25
                
            weighted_signals[indicator_name] = {
                'base_score': base_score,
                'weight': weight,
                'weighted_score': base_score * weight
            }
    
    # Construct the full output
    output = {
        'agent_name': agent_name,
        'agent_type': agent_type,
        'date': date_str,
        'timestamp': f"{date_str}T{datetime.now().strftime('%H:%M:%S')}Z",
        'score': score,
        'action': action,
        'confidence': confidence,
        'rationale': rationale,
        'weighted_signals': weighted_signals
    }
    
    return output


def save_output(agent_name, output, date_str):
    """
    Save agent output to a file.
    
    Args:
        agent_name: Name of the agent
        output: Output dictionary
        date_str: Date string (YYYY-MM-DD)
        
    Returns:
        Path to the saved file
    """
    # Create agent-specific directory
    agent_dir = os.path.join(OUTPUTS_DIR, agent_name.lower().replace(' ', '_'))
    os.makedirs(agent_dir, exist_ok=True)
    
    # Save output
    output_path = os.path.join(agent_dir, f"{date_str}.json")
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Saved output for {agent_name} to {output_path}")
    return output_path


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate mock agent outputs')
    parser.add_argument('--date', help='Date to generate outputs for (YYYY-MM-DD)')
    parser.add_argument('--seed', type=int, help='Random seed for reproducible outputs')
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
    
    # Set up directories
    setup_directories()
    
    # Determine date
    date_str = args.date or datetime.now().strftime('%Y-%m-%d')
    
    print(f"\nGenerating mock agent outputs for {date_str}:")
    
    # Load agent specs and indicators
    agent_specs = load_agent_specs()
    indicators = load_indicators(date_str)
    
    if not indicators:
        print("No indicators found. Run generate_mock_data.py first.")
        return 1
    
    if not agent_specs:
        print("No agent specifications found.")
        return 1
    
    # Generate and save mock outputs for each agent
    for agent_spec in agent_specs:
        agent_name = agent_spec.get('name', 'Unknown')
        output = generate_mock_output(agent_spec, indicators, date_str)
        save_output(agent_name, output, date_str)
    
    print("\nMock agent output generation complete.")
    return 0


if __name__ == "__main__":
    exit(main())
