#!/usr/bin/env python3
"""
Crypto Analyst Agent Swarm - Orchestration System
-------------------------------------------------
This script handles the passive ingestion of agent definitions and will later 
coordinate the agent swarm after all agents are loaded.
"""

import json
import os
import sys
from pathlib import Path

# Constants
AGENTS_DIR = Path(__file__).parent / "agents"

def save_agent_spec(agent_data):
    """
    Store an agent specification to the appropriate file.
    
    Args:
        agent_data (dict): The agent specification data
        
    Returns:
        str: The name of the agent that was saved
    """
    # Extract the agent name
    agent_name = agent_data.get("agent_name")
    if not agent_name:
        raise ValueError("Agent specification must include 'agent_name'")
    
    # Ensure the agents directory exists
    AGENTS_DIR.mkdir(exist_ok=True, parents=True)
    
    # Save the specification to a JSON file
    agent_file = AGENTS_DIR / f"{agent_name}.json"
    with open(agent_file, 'w') as f:
        json.dump(agent_data, f, indent=2)
    
    return agent_name

def list_loaded_agents():
    """
    List all agent specifications that have been loaded.
    
    Returns:
        list: Names of all loaded agents
    """
    if not AGENTS_DIR.exists():
        return []
    
    return [f.stem for f in AGENTS_DIR.glob("*.json")]

def activate_swarm():
    """
    Activate the agent swarm after all agents have been loaded.
    This will be implemented when the final signal is received.
    """
    agents = list_loaded_agents()
    return f"Swarm activated with {len(agents)} agents: {', '.join(agents)}"

# Command-line interface for testing
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            agents = list_loaded_agents()
            print(f"Loaded agents ({len(agents)}): {', '.join(agents)}")
            
        elif command == "activate":
            result = activate_swarm()
            print(result)
            
        elif command == "save" and len(sys.argv) > 2:
            try:
                with open(sys.argv[2], 'r') as f:
                    agent_data = json.load(f)
                agent_name = save_agent_spec(agent_data)
                print(f"ACK:{agent_name}")
            except Exception as e:
                print(f"Error: {e}")
    else:
        print("Usage: orchestration.py [list|activate|save <json_file>]")
