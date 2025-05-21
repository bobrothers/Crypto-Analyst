#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
refresh_indicators.py
---------------------
Fetches and updates all market indicators used by the Crypto Analyst Agent Swarm.
Each indicator is retrieved from its respective data source and saved in a standardized format.

This script is called as the first step in the daily_swarm_workflow defined in swarm.yaml.
"""

import os
import json
import logging
import argparse
import asyncio
import aiohttp
import csv
import random
from io import StringIO
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('refresh_indicators')

# Define output directory for storing indicator data
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data/indicators')

# Cache to store indicator results during runtime
INDICATOR_CACHE = {}


def setup_data_directory() -> None:
    """Create the data directory structure if it doesn't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info(f"Ensuring data directory exists: {DATA_DIR}")
    
    # Create subdirectories for each indicator
    indicator_dirs = ['cbbi', 'rainbow_bands', 'pi_cycle']
    for indicator in indicator_dirs:
        indicator_path = os.path.join(DATA_DIR, indicator)
        os.makedirs(indicator_path, exist_ok=True)
        logger.debug(f"Created indicator directory: {indicator_path}")


def get_signal_from_value(indicator_name: str, value: float) -> str:
    """
    Determine signal (bullish/bearish/neutral) based on indicator value.
    
    Args:
        indicator_name: Name of the indicator
        value: The indicator value
    
    Returns:
        Signal string: 'bullish', 'bearish', or 'neutral'
    """
    # CBBI signal thresholds
    if indicator_name.lower() == 'cbbi':
        if value >= 0.8:
            return 'bearish'
        elif value <= 0.3:
            return 'bullish'
        else:
            return 'neutral'
    
    # Rainbow Bands signal thresholds (band position 1-8)
    elif indicator_name.lower() == 'rainbow_bands':
        if value >= 7:
            return 'bearish'
        elif value <= 2:
            return 'bullish'
        else:
            return 'neutral'
    
    # Pi Cycle signal thresholds (ratio approaching 1.0 is bearish)
    elif indicator_name.lower() == 'pi_cycle':
        if value >= 0.95:
            return 'bearish'
        elif value <= 0.5:
            return 'bullish'
        else:
            return 'neutral'
    
    # Default for unknown indicators
    else:
        if value >= 70:
            return 'bearish'
        elif value <= 30:
            return 'bullish'
        else:
            return 'neutral'


def save_indicator(indicator: Dict[str, Any], date_str: Optional[str] = None) -> None:
    """
    Save an indicator to the data directory.
    
    Args:
        indicator: A dictionary with the indicator data
                  Must contain 'name', 'timestamp', and 'value' keys
        date_str: Optional date string in YYYY-MM-DD format, defaults to today
    """
    if not all(k in indicator for k in ['name', 'timestamp', 'value']):
        raise ValueError("Indicator must contain 'name', 'timestamp', and 'value' keys")
    
    # Convert indicator name to directory name
    indicator_name = indicator['name'].lower().replace(' ', '_')
    indicator_dir = os.path.join(DATA_DIR, indicator_name)
    
    # Ensure indicator directory exists
    os.makedirs(indicator_dir, exist_ok=True)
    
    # Use provided date or extract from timestamp
    if date_str is None:
        dt = datetime.fromisoformat(indicator['timestamp'].replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d')
    
    file_path = os.path.join(indicator_dir, f"{date_str}.json")
    
    # Save indicator data
    with open(file_path, 'w') as f:
        json.dump(indicator, f, indent=2)
    
    logger.info(f"Saved indicator: {indicator_name} for date {date_str} with value: {indicator['value']}")


async def fetch_with_retry(session: aiohttp.ClientSession, 
                          url: str, 
                          max_retries: int = 3, 
                          base_delay: float = 1.0) -> Tuple[bool, Union[Dict, str, None]]:
    """
    Fetch data from URL with exponential backoff retry logic.
    
    Args:
        session: aiohttp client session
        url: URL to fetch
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
    
    Returns:
        Tuple containing (success_flag, response_data)
    """
    for retry in range(max_retries):
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    # Check content type to determine response format
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'application/json' in content_type:
                        return True, await response.json()
                    else:
                        return True, await response.text()
                        
                logger.warning(f"Failed to fetch {url}, status: {response.status}, attempt: {retry+1}/{max_retries}")
                
                # If we get rate limited, wait longer
                if response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get('Retry-After', base_delay * (2 ** retry)))
                    await asyncio.sleep(retry_after)
                else:
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** retry) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                    
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"Error fetching {url}: {str(e)}, attempt: {retry+1}/{max_retries}")
            
            # Exponential backoff with jitter
            delay = base_delay * (2 ** retry) + random.uniform(0, 1)
            await asyncio.sleep(delay)
    
    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    return False, None


async def fetch_cbbi(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Fetch the Crypto Bull/Bear Index from CBBI API.
    
    Args:
        session: aiohttp client session
    
    Returns:
        A dictionary with the indicator data in the format:
        {'name': 'CBBI', 'timestamp': ISO-8601 string, 'value': float, 'signal': str}
    """
    url = "https://ccbitcoinindex.appspot.com/api/score"
    logger.info(f"Fetching CBBI from {url}")
    
    # Check cache first
    today = datetime.now().strftime('%Y-%m-%d')
    cache_key = f"cbbi_{today}"
    if cache_key in INDICATOR_CACHE:
        logger.info(f"Using cached CBBI data for {today}")
        return INDICATOR_CACHE[cache_key]
    
    success, data = await fetch_with_retry(session, url)
    
    if success and data:
        try:
            if isinstance(data, str):
                data = json.loads(data)
                
            # Extract the score from the response
            cbbi_value = float(data.get('score', 0))
            timestamp = datetime.now().isoformat()
            
            # Determine signal based on value
            signal = get_signal_from_value('cbbi', cbbi_value)
            
            result = {
                'name': 'CBBI',
                'timestamp': timestamp,
                'value': cbbi_value,
                'signal': signal
            }
            
            # Cache the result
            INDICATOR_CACHE[cache_key] = result
            return result
            
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing CBBI data: {str(e)}")
    
    # Return fallback data
    logger.warning("Using fallback CBBI data")
    return {
        'name': 'CBBI',
        'timestamp': datetime.now().isoformat(),
        'value': 0.5,  # Neutral fallback
        'signal': 'neutral'
    }


async def fetch_rainbow_bands(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Fetch Bitcoin Rainbow Chart band data from Blockchain Center API.
    
    Args:
        session: aiohttp client session
    
    Returns:
        A dictionary with the indicator data in the format:
        {'name': 'Rainbow Bands', 'timestamp': ISO-8601 string, 'value': float, 'signal': str}
    """
    url = "https://api.blockchaincenter.net/v1/rainbow"
    logger.info(f"Fetching Rainbow Bands from {url}")
    
    # Check cache first
    today = datetime.now().strftime('%Y-%m-%d')
    cache_key = f"rainbow_bands_{today}"
    if cache_key in INDICATOR_CACHE:
        logger.info(f"Using cached Rainbow Bands data for {today}")
        return INDICATOR_CACHE[cache_key]
    
    success, data = await fetch_with_retry(session, url)
    
    if success and data:
        try:
            # Parse CSV data
            csv_reader = csv.reader(StringIO(data))
            rows = list(csv_reader)
            
            # Skip header row and find the most recent data point
            if len(rows) > 1:
                latest_row = rows[-1]  # Assuming the last row is the most recent
                
                # Extract date and price
                date_str = latest_row[0]
                price = float(latest_row[1])
                
                # Determine which band the price falls into
                # Bands are columns 2-9 in the CSV, from bottom to top
                band_position = 1  # Default to lowest band
                
                for i in range(2, 10):
                    if i < len(latest_row) and price > float(latest_row[i]):
                        band_position = i - 1
                
                # Convert date string to timestamp
                timestamp = datetime.strptime(date_str, '%Y-%m-%d').isoformat()
                
                # Determine signal based on band position
                signal = get_signal_from_value('rainbow_bands', band_position)
                
                result = {
                    'name': 'Rainbow Bands',
                    'timestamp': timestamp,
                    'value': band_position,
                    'signal': signal
                }
                
                # Cache the result
                INDICATOR_CACHE[cache_key] = result
                return result
        
        except (IndexError, ValueError, csv.Error) as e:
            logger.error(f"Error parsing Rainbow Bands data: {str(e)}")
    
    # Return fallback data
    logger.warning("Using fallback Rainbow Bands data")
    return {
        'name': 'Rainbow Bands',
        'timestamp': datetime.now().isoformat(),
        'value': 4.0,  # Middle band as fallback
        'signal': 'neutral'
    }


async def fetch_pi_cycle(session: aiohttp.ClientSession) -> Dict[str, Any]:
    """
    Fetch the Pi Cycle Top Indicator (ratio of 111-day MA / 350-day MA).
    
    Args:
        session: aiohttp client session
    
    Returns:
        A dictionary with the indicator data in the format:
        {'name': 'Pi Cycle', 'timestamp': ISO-8601 string, 'value': float, 'signal': str}
    """
    # TODO: Replace with actual Glassnode or alternative API endpoint
    # For now, we'll use a placeholder approach
    logger.info("Calculating Pi Cycle indicator")
    
    # Check cache first
    today = datetime.now().strftime('%Y-%m-%d')
    cache_key = f"pi_cycle_{today}"
    if cache_key in INDICATOR_CACHE:
        logger.info(f"Using cached Pi Cycle data for {today}")
        return INDICATOR_CACHE[cache_key]
    
    # Placeholder implementation
    # In a real implementation, we would:
    # 1. Fetch BTC price history for at least 350 days
    # 2. Calculate the 111-day moving average
    # 3. Calculate the 350-day moving average
    # 4. Compute the ratio: 111-day MA / 350-day MA
    
    # For demonstration purposes, we'll generate a synthetic value
    # that varies based on the day of the month
    day_of_month = datetime.now().day
    synthetic_ratio = 0.5 + (day_of_month / 100)  # Ranges from 0.5 to ~0.8
    
    # Determine signal based on the ratio
    signal = get_signal_from_value('pi_cycle', synthetic_ratio)
    
    result = {
        'name': 'Pi Cycle',
        'timestamp': datetime.now().isoformat(),
        'value': synthetic_ratio,
        'signal': signal
    }
    
    # Cache the result
    INDICATOR_CACHE[cache_key] = result
    return result


async def fetch_all_indicators() -> List[Dict[str, Any]]:
    """
    Fetch all indicators asynchronously and return them as a list.
    
    Returns:
        A list of indicator dictionaries
    """
    async with aiohttp.ClientSession() as session:
        # Create tasks for all indicators
        tasks = [
            fetch_cbbi(session),
            fetch_rainbow_bands(session),
            fetch_pi_cycle(session)
        ]
        
        # Execute all tasks concurrently
        indicators = await asyncio.gather(*tasks)
        
        logger.info(f"Fetched {len(indicators)} indicators")
        return indicators


def sync_fetch_all_indicators() -> List[Dict[str, Any]]:
    """
    Synchronous wrapper for fetch_all_indicators.
    
    Returns:
        A list of indicator dictionaries
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(fetch_all_indicators())


def main(save_to_file: bool = True, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Main function to refresh all indicators.
    
    Args:
        save_to_file: Whether to save the indicators to files
        date_str: Optional date string in YYYY-MM-DD format
        
    Returns:
        A list of all refreshed indicators
    """
    logger.info("Starting indicator refresh")
    
    if save_to_file:
        setup_data_directory()
    
    indicators = sync_fetch_all_indicators()
    
    if save_to_file:
        for indicator in indicators:
            save_indicator(indicator, date_str)
    
    logger.info("Indicator refresh complete")
    return indicators


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Refresh crypto market indicators')
    parser.add_argument('--no-save', action='store_true', help='Do not save indicators to files')
    parser.add_argument('--date', help='Date to save indicators for (YYYY-MM-DD)')
    parser.add_argument('--output', choices=['json', 'pretty'], default='pretty',
                        help='Output format (default: pretty)')
    parser.add_argument('--dry-run', action='store_true', help='Use mock data instead of making API calls')
    args = parser.parse_args()
    
    indicators = main(save_to_file=not args.no_save, date_str=args.date)
    
    if args.output == 'json':
        print(json.dumps(indicators))
    else:
        for indicator in indicators:
            print(f"{indicator['name']}: {indicator['value']} ({indicator['signal']}) - {indicator['timestamp']}")
