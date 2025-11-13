#!/bin/bash
# Convenience script to run the laget.se scraper

# Activate virtual environment
source venv/bin/activate

# Run the scraper with the scrape command
python laget_scraper.py scrape "$@"
