# Crypto Analyst Agent Swarm

This project contains the orchestration layer for a multi-agent system designed to analyze cryptocurrency markets.

## Purpose

The system ingests multiple specialized agent definitions, each with their own expertise, data feeds, and analysis methods. These agents will work together to provide comprehensive crypto market analysis.

## Loading Process

1. Agent definitions are loaded sequentially and stored individually
2. After all agents are loaded, the orchestration system activates
3. The system then coordinates agent activities according to specified workflows

## Directory Structure

- `/agents/` - Contains individual agent definitions
- `/orchestration/` - Contains the coordination system

## Status

Currently in agent loading phase. Waiting for all agent definitions before activation.
