#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/test_run_agent.py
------------------------
Unit tests for the agent runner system.
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import the script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import modules to test
from agents.base_agent import BaseAgent
from agents.run_agent import (
    load_agent_spec,
    load_indicators,
    instantiate_agent,
    save_output,
    run_agent
)


# Sample agent specification for testing
SAMPLE_AGENT_SPEC = {
    "name": "Test Agent",
    "type": "rule_based",
    "weights": {
        "CBBI": 0.4,
        "Rainbow Bands": 0.3,
        "Pi Cycle": 0.3
    },
    "thresholds": {
        "bullish": 70,
        "bearish": 30
    }
}

# Sample indicators for testing
SAMPLE_INDICATORS = {
    "CBBI": {"name": "CBBI", "value": 0.65, "signal": "neutral", "timestamp": "2025-05-20T00:00:00Z"},
    "Rainbow Bands": {"name": "Rainbow Bands", "value": 3, "signal": "bullish", "timestamp": "2025-05-20T00:00:00Z"},
    "Pi Cycle": {"name": "Pi Cycle", "value": 0.85, "signal": "bearish", "timestamp": "2025-05-20T00:00:00Z"}
}


# Test implementation of BaseAgent for testing
class TestAgent(BaseAgent):
    """Test agent implementation."""
    
    def analyze(self):
        """Implement the abstract method."""
        weighted_signals = self.weight_signals()
        score = self.calculate_composite_score(weighted_signals)
        action = self.determine_action(score)
        
        return {
            'score': score,
            'action': action,
            'confidence': 0.8,
            'rationale': "This is a test agent analysis.",
            'weighted_signals': weighted_signals
        }


# Fixtures
@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = tempfile.mkdtemp()
    
    # Create subdirectories
    os.makedirs(os.path.join(temp_dir, 'agents'), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, 'indicators'), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, 'outputs'), exist_ok=True)
    
    # Create sample agent spec file
    agent_path = os.path.join(temp_dir, 'agents', 'Test Agent.json')
    with open(agent_path, 'w') as f:
        json.dump(SAMPLE_AGENT_SPEC, f)
    
    # Create sample indicator directories and files
    for indicator_name, indicator_data in SAMPLE_INDICATORS.items():
        indicator_dir = os.path.join(temp_dir, 'indicators', indicator_name.lower().replace(' ', '_'))
        os.makedirs(indicator_dir, exist_ok=True)
        
        # Create indicator file for test date
        indicator_file = os.path.join(indicator_dir, '2025-05-20.json')
        with open(indicator_file, 'w') as f:
            json.dump(indicator_data, f)
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


# Tests
def test_load_agent_spec(temp_data_dir):
    """Test loading an agent specification."""
    with patch('agents.run_agent.AGENT_SPECS_DIR', os.path.join(temp_data_dir, 'agents')):
        spec = load_agent_spec('Test Agent')
        
        assert spec['name'] == 'Test Agent'
        assert spec['type'] == 'rule_based'
        assert 'weights' in spec
        assert spec['weights']['CBBI'] == 0.4


def test_load_indicators(temp_data_dir):
    """Test loading indicators for a date."""
    with patch('agents.run_agent.INDICATORS_DIR', os.path.join(temp_data_dir, 'indicators')):
        indicators = load_indicators('2025-05-20')
        
        assert len(indicators) == 3
        assert 'CBBI' in indicators
        assert indicators['CBBI']['value'] == 0.65
        assert indicators['Rainbow Bands']['signal'] == 'bullish'


def test_instantiate_agent():
    """Test creating an agent instance."""
    with patch('agents.run_agent.AGENT_CLASSES', {'rule_based': TestAgent}):
        agent = instantiate_agent(SAMPLE_AGENT_SPEC, SAMPLE_INDICATORS)
        
        assert isinstance(agent, TestAgent)
        assert agent.name == 'Test Agent'
        assert len(agent.indicators) == 3


def test_save_output(temp_data_dir):
    """Test saving agent output to a file."""
    output_data = {
        'score': 65.0,
        'action': 'BUY',
        'confidence': 0.8,
        'rationale': 'Test rationale'
    }
    
    with patch('agents.run_agent.OUTPUTS_DIR', os.path.join(temp_data_dir, 'outputs')):
        output_path = save_output('Test Agent', '2025-05-20', output_data)
        
        # Check that the file exists
        assert os.path.exists(output_path)
        
        # Check file contents
        with open(output_path, 'r') as f:
            saved_data = json.load(f)
            
            assert saved_data['score'] == 65.0
            assert saved_data['action'] == 'BUY'
            assert saved_data['agent_name'] == 'Test Agent'
            assert saved_data['date'] == '2025-05-20'


def test_weight_signals():
    """Test weighting of indicator signals."""
    agent = TestAgent(SAMPLE_AGENT_SPEC, SAMPLE_INDICATORS)
    weighted_signals = agent.weight_signals()
    
    assert len(weighted_signals) == 3
    assert weighted_signals['CBBI']['weight'] == 0.4
    assert weighted_signals['Rainbow Bands']['base_score'] == 75  # bullish
    assert weighted_signals['Pi Cycle']['base_score'] == 25  # bearish
    
    # Check weighted scores
    assert weighted_signals['CBBI']['weighted_score'] == 50 * 0.4  # neutral * weight
    assert weighted_signals['Rainbow Bands']['weighted_score'] == 75 * 0.3  # bullish * weight
    assert weighted_signals['Pi Cycle']['weighted_score'] == 25 * 0.3  # bearish * weight


def test_composite_score():
    """Test calculation of composite score."""
    agent = TestAgent(SAMPLE_AGENT_SPEC, SAMPLE_INDICATORS)
    weighted_signals = agent.weight_signals()
    score = agent.calculate_composite_score(weighted_signals)
    
    # Expected: (50*0.4 + 75*0.3 + 25*0.3) = 20 + 22.5 + 7.5 = 50
    expected_score = 50
    assert score == pytest.approx(expected_score, abs=1)


def test_determine_action():
    """Test determination of recommended action based on score."""
    agent = TestAgent(SAMPLE_AGENT_SPEC, SAMPLE_INDICATORS)
    
    assert agent.determine_action(80) == "STRONG_BUY"
    assert agent.determine_action(65) == "BUY"
    assert agent.determine_action(50) == "HOLD"
    assert agent.determine_action(35) == "SELL"
    assert agent.determine_action(20) == "STRONG_SELL"


def test_run_agent_integration(temp_data_dir):
    """Integration test for the run_agent function."""
    with patch('agents.run_agent.AGENT_SPECS_DIR', os.path.join(temp_data_dir, 'agents')), \
         patch('agents.run_agent.INDICATORS_DIR', os.path.join(temp_data_dir, 'indicators')), \
         patch('agents.run_agent.OUTPUTS_DIR', os.path.join(temp_data_dir, 'outputs')), \
         patch('agents.run_agent.AGENT_CLASSES', {'rule_based': TestAgent}):
        
        # Run the agent
        result = run_agent('Test Agent', '2025-05-20')
        
        # Check result
        assert 'score' in result
        assert 'action' in result
        assert 'confidence' in result
        assert 'rationale' in result
        
        # Check that output file was created
        output_path = os.path.join(temp_data_dir, 'outputs', 'test_agent', '2025-05-20.json')
        assert os.path.exists(output_path)


def test_cli_exit_code():
    """Test that the CLI returns the correct exit code."""
    with patch('agents.run_agent.run_agent') as mock_run_agent, \
         patch('sys.argv', ['run_agent.py', '--agent', 'Test Agent', '--date', '2025-05-20']):
        
        mock_run_agent.return_value = {'score': 50, 'action': 'HOLD'}
        
        from agents.run_agent import main
        exit_code = main()
        
        assert exit_code == 0


def test_cli_error_handling():
    """Test error handling in the CLI."""
    with patch('agents.run_agent.run_agent') as mock_run_agent, \
         patch('sys.argv', ['run_agent.py', '--agent', 'Test Agent', '--date', '2025-05-20']):
        
        mock_run_agent.side_effect = Exception("Test error")
        
        from agents.run_agent import main
        exit_code = main()
        
        assert exit_code == 1
