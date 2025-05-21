#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_mock_data.py
---------------------
Generates mock indicator data for testing the Crypto Analyst Agent Swarm.
This script creates realistic test data for all required indicators.
"""

import os
import json
import argparse
import random
from datetime import datetime, timedelta

# Define paths
DATA_DIR = os.getenv('DATA_STORAGE_PATH', 'data')
INDICATORS_DIR = os.path.join(DATA_DIR, 'indicators')


def setup_directories():
    """Ensure all required directories exist."""
    os.makedirs(INDICATORS_DIR, exist_ok=True)
    
    # Create subdirectories for each indicator
    for indicator in ['cbbi', 'rainbow_bands', 'pi_cycle']:
        os.makedirs(os.path.join(INDICATORS_DIR, indicator), exist_ok=True)
    
    print(f"Created indicator directories in {INDICATORS_DIR}")


def generate_cbbi_data(date_str):
    """
    Generate mock CBBI (Crypto Bull/Bear Index) data.
    CBBI ranges from 0-1 where values closer to 1 indicate market euphoria.
    """
    # Generate a value between 0 and 1
    value = round(random.uniform(0.2, 0.9), 2)
    
    # Determine signal based on value
    if value < 0.3:
        signal = "bullish"
    elif value < 0.7:
        signal = "neutral"
    else:
        signal = "bearish"
    
    data = {
        "name": "CBBI",
        "value": value,
        "signal": signal,
        "timestamp": f"{date_str}T12:00:00Z",
        "source": "mock_data",
        "url": "https://cbbi.info/",
        "description": "Crypto Bull/Bear Index - A composite of different indicators to gauge market sentiment"
    }
    
    # Save to file
    filepath = os.path.join(INDICATORS_DIR, "cbbi", f"{date_str}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Generated CBBI data for {date_str}: {value} ({signal})")
    return data


def generate_rainbow_bands_data(date_str):
    """
    Generate mock Rainbow Bands data.
    The band values range from 1 (deep value) to 9 (maximum bubble).
    """
    # Generate a band value between 1 and 9
    value = random.randint(1, 9)
    
    # Determine signal based on band
    if value <= 3:
        signal = "bullish"
    elif value <= 6:
        signal = "neutral"
    else:
        signal = "bearish"
    
    # Calculate a mock price based on band
    base_price = 40000  # Base BTC price
    price_multiplier = 1.1 ** value  # Each band is ~10% higher
    price = round(base_price * price_multiplier, 2)
    
    data = {
        "name": "Rainbow Bands",
        "value": value,
        "signal": signal,
        "price": price,
        "band_name": [
            "Maximum Bubble", "Sell. Seriously, Sell", "FOMO Intensifies", 
            "Is This a Bubble?", "HODL", "Still Cheap", "Accumulate", 
            "Buy", "Basically a Fire Sale"
        ][9-value],
        "timestamp": f"{date_str}T12:00:00Z",
        "source": "mock_data",
        "url": "https://www.blockchaincenter.net/en/bitcoin-rainbow-chart/",
        "description": "Bitcoin Rainbow Price Chart - logarithmic regression bands visualizing market cycles"
    }
    
    # Save to file
    filepath = os.path.join(INDICATORS_DIR, "rainbow_bands", f"{date_str}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Generated Rainbow Bands data for {date_str}: Band {value} ({signal})")
    return data


def generate_pi_cycle_data(date_str):
    """
    Generate mock Pi Cycle data.
    Pi Cycle values range from 0 to 1, where values close to 1 indicate potential market tops.
    """
    # Generate a value between 0 and 1
    value = round(random.uniform(0.3, 0.98), 2)
    
    # Determine signal based on value
    if value < 0.5:
        signal = "bullish"
    elif value < 0.85:
        signal = "neutral"
    else:
        signal = "bearish"
    
    data = {
        "name": "Pi Cycle",
        "value": value,
        "signal": signal,
        "ma_111": 42000,  # Mock 111-day moving average
        "ma_350x2": round(42000 * value, 2),  # Mock 2x 350-day moving average
        "timestamp": f"{date_str}T12:00:00Z",
        "source": "mock_data",
        "url": "https://www.lookintobitcoin.com/charts/pi-cycle-top-indicator/",
        "description": "Pi Cycle Top Indicator - identifies market cycle tops based on the relationship between two moving averages"
    }
    
    # Save to file
    filepath = os.path.join(INDICATORS_DIR, "pi_cycle", f"{date_str}.json")
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Generated Pi Cycle data for {date_str}: {value} ({signal})")
    return data


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Generate mock indicator data')
    parser.add_argument('--date', help='Date to generate data for (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, default=1, help='Number of days to generate data for')
    parser.add_argument('--seed', type=int, help='Random seed for reproducible data')
    args = parser.parse_args()
    
    # Set random seed if provided
    if args.seed:
        random.seed(args.seed)
    
    # Set up directories
    setup_directories()
    
    # Determine start date
    if args.date:
        start_date = datetime.strptime(args.date, '%Y-%m-%d')
    else:
        start_date = datetime.now()
    
    # Generate data for each day
    for i in range(args.days):
        date = start_date - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        
        print(f"\nGenerating mock data for {date_str}:")
        
        # Generate indicator data
        cbbi = generate_cbbi_data(date_str)
        rainbow = generate_rainbow_bands_data(date_str)
        pi_cycle = generate_pi_cycle_data(date_str)
        
        # For mock data, add a bit of correlation
        if random.random() < 0.7:
            # 70% chance that indicators correlate
            if cbbi['signal'] == 'bullish':
                rainbow['signal'] = random.choice(['bullish', 'neutral'])
                pi_cycle['signal'] = random.choice(['bullish', 'neutral'])
            elif cbbi['signal'] == 'bearish':
                rainbow['signal'] = random.choice(['bearish', 'neutral'])
                pi_cycle['signal'] = random.choice(['bearish', 'neutral'])
    
    print("\nMock data generation complete.")
    return 0


if __name__ == "__main__":
    exit(main())
