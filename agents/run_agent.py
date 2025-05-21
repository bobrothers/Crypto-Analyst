#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_agent.py
------------
CLI entry point for running individual agents within the Crypto Analyst Agent Swarm.
Loads agent specifications from JSON files and executes their analysis methods.

This script is called by the daily_swarm_workflow in parallel for each agent.
"""

import os
import sys
import json
import logging
import argparse
import importlib
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Type

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('agent_runner')

# Define paths for agent specs and outputs
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data')
AGENT_SPECS_DIR = os.path.join(DATA_DIR, 'agents')
INDICATORS_DIR = os.path.join(DATA_DIR, 'indicators')
OUTPUTS_DIR = os.path.join(DATA_DIR, 'outputs')

# Import the base agent class
from agents.base_agent import BaseAgent

# Dictionary mapping agent types to their implementation classes
AGENT_CLASSES = {}


def register_agent_class(agent_type: str, agent_class: Type[BaseAgent]) -> None:
    """
    Register an agent implementation class for a specific agent type.
    
    Args:
        agent_type: String identifier for the agent type
        agent_class: Class implementing the BaseAgent interface
    """
    AGENT_CLASSES[agent_type] = agent_class
    logger.debug(f"Registered agent class for type: {agent_type}")


def load_agent_spec(agent_name: str) -> Dict[str, Any]:
    """
    Load an agent's specification from its JSON file.
    
    Args:
        agent_name: Name of the agent to load
    
    Returns:
        Dictionary containing the agent's specification
    
    Raises:
        FileNotFoundError: If the agent specification cannot be found
    """
    # Normalize agent filename
    agent_filename = f"{agent_name}.json"
    agent_path = os.path.join(AGENT_SPECS_DIR, agent_filename)
    
    logger.info(f"Loading agent spec from {agent_path}")
    
    try:
        with open(agent_path, 'r') as f:
            spec = json.load(f)
            if 'name' not in spec:
                spec['name'] = agent_name
            return spec
    except FileNotFoundError:
        logger.error(f"Agent specification not found: {agent_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in agent specification: {agent_path}")
        raise


def load_indicators(date: Optional[str] = None, mock_data: bool = False) -> Dict[str, Any]:
    """
    Load indicator data for the specified date.
    
    Args:
        date: Date string in YYYY-MM-DD format (default: today)
        mock_data: Whether to use mock data instead of real indicator data
    
    Returns:
        Dictionary mapping indicator names to their data
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    indicators = {}
    
    if mock_data:
        # Use mock data for testing
        logger.info("Using mock indicator data")
        indicators = {
            'CBBI': {'value': 0.65, 'signal': 'neutral', 'timestamp': datetime.now().isoformat()},
            'Rainbow Bands': {'value': 5, 'signal': 'neutral', 'timestamp': datetime.now().isoformat()},
            'Pi Cycle': {'value': 0.7, 'signal': 'neutral', 'timestamp': datetime.now().isoformat()}
        }
    else:
        # Find all indicator directories
        for indicator_dir in os.listdir(INDICATORS_DIR):
            indicator_path = os.path.join(INDICATORS_DIR, indicator_dir)
            
            if os.path.isdir(indicator_path):
                # Look for the file for the specified date
                date_file = os.path.join(indicator_path, f"{date}.json")
                
                if os.path.exists(date_file):
                    try:
                        with open(date_file, 'r') as f:
                            indicator_data = json.load(f)
                            indicators[indicator_data.get('name', indicator_dir)] = indicator_data
                    except (json.JSONDecodeError, IOError) as e:
                        logger.error(f"Error loading indicator {indicator_dir} for {date}: {str(e)}")
    
    logger.info(f"Loaded {len(indicators)} indicators for date {date}")
    return indicators


def instantiate_agent(spec: Dict[str, Any], indicators: Dict[str, Any]) -> BaseAgent:
    """
    Create an agent instance based on the specification.
    
    Args:
        spec: Agent specification dictionary
        indicators: Dictionary of available indicators
    
    Returns:
        Instance of an agent class that extends BaseAgent
    
    Raises:
        ValueError: If the agent type is not supported
    """
    agent_type = spec.get('type', 'rule_based').lower()
    
    # Import agent class if not already registered
    if agent_type not in AGENT_CLASSES:
        try:
            module_name = f"agents.{agent_type}_agent"
            module = importlib.import_module(module_name)
            class_name = ''.join(word.capitalize() for word in agent_type.split('_')) + 'Agent'
            agent_class = getattr(module, class_name)
            register_agent_class(agent_type, agent_class)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import agent class for type {agent_type}: {str(e)}")
            raise ValueError(f"Unsupported agent type: {agent_type}")
    
    # Create instance of the agent class
    agent_class = AGENT_CLASSES[agent_type]
    return agent_class(spec, indicators)


def save_output(agent_name: str, date: str, output: Dict[str, Any]) -> str:
    """
    Save agent output to a file.
    
    Args:
        agent_name: Name of the agent
        date: Date string in YYYY-MM-DD format
        output: Dictionary of agent output data
    
    Returns:
        Path to the saved output file
    """
    # Create agent output directory
    agent_dir = os.path.join(OUTPUTS_DIR, agent_name.replace(' ', '_').lower())
    os.makedirs(agent_dir, exist_ok=True)
    
    # Create output file path
    output_path = os.path.join(agent_dir, f"{date}.json")
    
    # Add metadata to output
    output['agent_name'] = agent_name
    output['date'] = date
    output['timestamp'] = datetime.now().isoformat()
    
    # Save to file
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"Saved output to {output_path}")
    return output_path


def run_agent(agent_name: str, date: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """
    Run an agent's analysis and save the results.
    
    Args:
        agent_name: Name of the agent to run
        date: Date to analyze (YYYY-MM-DD format)
        dry_run: Whether to use mock data instead of real indicators
    
    Returns:
        Dictionary containing the agent's analysis results
    
    Raises:
        Exception: If any error occurs during agent execution
    """
    try:
        # Use today's date if none specified
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Load agent specification
        spec = load_agent_spec(agent_name)
        
        # Load indicators for the specified date
        indicators = load_indicators(date, mock_data=dry_run)
        
        # Create agent instance
        agent = instantiate_agent(spec, indicators)
        
        # Run analysis
        logger.info(f"Running analysis for {agent_name}")
        output = agent.analyze()
        
        # Save results
        save_output(agent_name, date, output)
        
        return output
    
    except Exception as e:
        logger.error(f"Error running agent {agent_name}: {str(e)}")
        raise


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Run a crypto analyst agent')
    parser.add_argument('--agent', required=True, help='Name of the agent to run')
    parser.add_argument('--date', help='Date to run the analysis for (YYYY-MM-DD)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Use mock data instead of actual indicators')
    parser.add_argument('--output', choices=['json', 'path', 'none'], default='none',
                       help='Output format (default: none)')
    args = parser.parse_args()
    
    try:
        # Run the agent
        results = run_agent(args.agent, args.date, args.dry_run)
        
        # Handle output based on user preference
        if args.output == 'json':
            print(json.dumps(results, indent=2))
        elif args.output == 'path':
            agent_dir = os.path.join(OUTPUTS_DIR, args.agent.replace(' ', '_').lower())
            date = args.date or datetime.now().strftime('%Y-%m-%d')
            print(os.path.join(agent_dir, f"{date}.json"))
        
        return 0
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
