#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_agent.py
-----------
LLM-based agent implementation for the Crypto Analyst Agent Swarm.
Uses an LLM to analyze market indicators and generate insights.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from . import base_agent

logger = logging.getLogger('agent.llm')

class LlmAgent(base_agent.BaseAgent):
    """
    LLM-based agent that uses large language models to analyze market data.
    
    This agent sends indicators and the agent's philosophy to an LLM,
    then parses the response into a standardized vote format.
    """
    
    def __init__(self, spec: Dict[str, Any], indicators: Dict[str, Any]):
        """
        Initialize the LLM agent.
        
        Args:
            spec: Agent specification dictionary
            indicators: Available indicators dictionary
        """
        super().__init__(spec, indicators)
        
        # Extract LLM-specific configuration
        self.model = spec.get('model', 'gpt-4')
        self.temperature = spec.get('temperature', 0.7)
        self.philosophy = spec.get('philosophy', '')
        self.prompt_template = spec.get('prompt_template', self._default_prompt_template())
        
        logger.info(f"Initialized LLM agent using {self.model}")
    
    def _default_prompt_template(self) -> str:
        """
        Provide a default prompt template if none specified.
        
        Returns:
            String template for the LLM prompt
        """
        return """
        You are {agent_name}, a cryptocurrency market analyst with the following philosophy:
        {philosophy}
        
        Today's market indicators:
        {indicators}
        
        Based on these indicators and your philosophy, provide:
        1. A market score from 0-100 (where 0 is extremely bearish, 100 is extremely bullish)
        2. A recommended action (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
        3. Your confidence level (0.0-1.0)
        4. A brief rationale for your analysis
        
        Format your response as a JSON object with the following structure:
        {{
            "score": <0-100>,
            "action": "<ACTION>",
            "confidence": <0.0-1.0>,
            "rationale": "<your explanation>"
        }}
        """
    
    def _format_indicators_for_prompt(self) -> str:
        """
        Format indicators into a human-readable string for the prompt.
        
        Returns:
            Formatted string of indicators
        """
        formatted = []
        for name, data in self.indicators.items():
            value = data.get('value', 'N/A')
            signal = data.get('signal', 'neutral')
            formatted.append(f"{name}: {value} ({signal})")
        
        return "\n".join(formatted)
    
    def _build_prompt(self) -> str:
        """
        Build the prompt to send to the LLM.
        
        Returns:
            Formatted prompt string
        """
        return self.prompt_template.format(
            agent_name=self.name,
            philosophy=self.philosophy,
            indicators=self._format_indicators_for_prompt()
        )
    
    def call_llm(self, prompt: str) -> str:
        """
        Call the LLM API with the given prompt.
        
        Args:
            prompt: The prompt to send to the LLM
        
        Returns:
            The LLM's response as a string
        """
        # TODO: Implement actual LLM API call
        # For now, return a mock response
        logger.info(f"Would call LLM API with prompt of length {len(prompt)}")
        
        # Mock response for demonstration
        mock_response = {
            "score": 65,
            "action": "BUY",
            "confidence": 0.75,
            "rationale": "Based on neutral indicators with slightly bullish bias."
        }
        
        return json.dumps(mock_response)
    
    def parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse the response from the LLM into a standardized format.
        
        Args:
            response: String response from the LLM
        
        Returns:
            Dictionary containing parsed response
        """
        try:
            # Try to parse as JSON
            parsed = json.loads(response)
            
            # Validate required fields
            required_fields = ['score', 'action', 'confidence', 'rationale']
            for field in required_fields:
                if field not in parsed:
                    logger.warning(f"Missing required field '{field}' in LLM response")
                    parsed[field] = None
            
            # Ensure score is in range 0-100
            if 'score' in parsed and parsed['score'] is not None:
                parsed['score'] = max(0, min(100, float(parsed['score'])))
            
            return parsed
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            
            # Fallback to default response
            return {
                'score': 50,
                'action': 'HOLD',
                'confidence': 0.5,
                'rationale': "Failed to parse LLM response."
            }
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze market indicators using the LLM.
        
        Returns:
            Dictionary containing analysis results
        """
        # Calculate weighted signals
        weighted_signals = self.weight_signals()
        
        # Calculate a baseline score
        baseline_score = self.calculate_composite_score(weighted_signals)
        baseline_action = self.determine_action(baseline_score)
        
        logger.info(f"Baseline analysis: score={baseline_score:.2f}, action={baseline_action}")
        
        # Build prompt for LLM
        prompt = self._build_prompt()
        
        # Call LLM
        llm_response = self.call_llm(prompt)
        
        # Parse response
        analysis = self.parse_llm_response(llm_response)
        
        # Add weighted signal data and baseline for reference
        analysis['weighted_signals'] = weighted_signals
        analysis['baseline'] = {
            'score': baseline_score,
            'action': baseline_action
        }
        
        logger.info(f"LLM analysis complete: score={analysis['score']:.2f}, action={analysis['action']}")
        
        return analysis
