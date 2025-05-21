#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
base_agent.py
------------
Abstract base class for all agent types in the Crypto Analyst Agent Swarm.
Defines the common interface and utility methods used by all agents.
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('base_agent')


class BaseAgent(ABC):
    """
    Abstract base class for all crypto analyst agents.
    
    This class defines the common interface and utility methods that all
    agent implementations must provide and can use.
    """
    
    def __init__(self, spec: Dict[str, Any], indicators: Dict[str, Any]):
        """
        Initialize the agent with its specification and available indicators.
        
        Args:
            spec: Dictionary containing the agent's specification
            indicators: Dictionary of indicator values {name: indicator_dict}
        """
        self.spec = spec
        self.indicators = indicators
        self.name = spec.get('name', 'UnknownAgent')
        self.type = spec.get('type', 'generic')
        self.weights = spec.get('weights', {})
        self.logger = logging.getLogger(f'agent.{self.name}')
        
        self.logger.info(f"Initialized {self.type} agent: {self.name}")
    
    def weight_signals(self) -> Dict[str, float]:
        """
        Apply weights from the agent's spec to the indicator signals.
        
        Returns:
            Dictionary mapping indicator names to their weighted scores
        """
        weighted_scores = {}
        
        # Default weights if none specified (equal weighting)
        if not self.weights and self.indicators:
            equal_weight = 1.0 / len(self.indicators)
            self.weights = {name: equal_weight for name in self.indicators}
        
        # Apply weights to each indicator
        for indicator_name, weight in self.weights.items():
            if indicator_name in self.indicators:
                indicator = self.indicators[indicator_name]
                
                # Convert signal to numeric score (0-100)
                signal = indicator.get('signal', 'neutral')
                raw_value = indicator.get('value', 50)
                
                # Simple mapping of signals to score ranges
                if signal == 'bullish':
                    base_score = 75
                elif signal == 'bearish':
                    base_score = 25
                else:  # neutral
                    base_score = 50
                
                # Apply weight
                weighted_scores[indicator_name] = {
                    'raw_value': raw_value,
                    'signal': signal,
                    'base_score': base_score,
                    'weight': weight,
                    'weighted_score': base_score * weight
                }
            else:
                self.logger.warning(f"Indicator '{indicator_name}' specified in weights but not found in available indicators")
        
        self.logger.info(f"Calculated weighted signals for {len(weighted_scores)} indicators")
        return weighted_scores
    
    def calculate_composite_score(self, weighted_signals: Dict[str, Dict[str, float]]) -> float:
        """
        Calculate a composite score from weighted signals.
        
        Args:
            weighted_signals: Dictionary of weighted signal data
        
        Returns:
            Composite score (0-100)
        """
        if not weighted_signals:
            self.logger.warning("No weighted signals available for score calculation")
            return 50.0  # Neutral default
        
        total_weight = sum(signal['weight'] for signal in weighted_signals.values())
        
        if total_weight == 0:
            self.logger.warning("Total weight is zero, returning neutral score")
            return 50.0
        
        weighted_sum = sum(signal['weighted_score'] for signal in weighted_signals.values())
        composite = weighted_sum / total_weight
        
        # Ensure score is in 0-100 range
        composite = max(0, min(100, composite))
        
        self.logger.info(f"Calculated composite score: {composite:.2f}")
        return composite
    
    def determine_action(self, score: float) -> str:
        """
        Determine the recommended action based on the score.
        
        Args:
            score: Composite score (0-100)
        
        Returns:
            Action string: 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', or 'STRONG_SELL'
        """
        if score >= 75:
            return "STRONG_BUY"
        elif score >= 60:
            return "BUY"
        elif score <= 25:
            return "STRONG_SELL"
        elif score <= 40:
            return "SELL"
        else:
            return "HOLD"
    
    @abstractmethod
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze available indicators and generate a vote.
        
        This is the main method that must be implemented by all agent subclasses.
        
        Returns:
            Dictionary containing vote information, including at minimum:
            {
                'score': float,  # 0-100 score
                'action': str,   # Recommended action
                'confidence': float,  # 0-1 confidence level
                'rationale': str  # Explanation for the vote
            }
        """
        pass
