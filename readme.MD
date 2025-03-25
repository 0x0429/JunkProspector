# JunkProspector Auction Analyzer

## Overview

**JunkProspector** is an automated tool designed to scrape auction sites, analyze item values, and identify potential bargains. Built with Python, Flask, Selenium, SQLite, and OpenAI's GPT-4, it systematically evaluates auction items based on market comparisons.

## Features
- **Automated Scraping:** Uses Selenium to navigate and scrape auction item details.
- **AI-Driven Analysis:** Leverages OpenAI GPT-4 to generate search queries and estimate market values.
- **Real-time Bargain Detection:** Identifies items priced significantly below market value.
- **Web Interface:** Simple Flask web app for initiating scraping and viewing analysis results.

## Installation

### Prerequisites
- Python 3.10+
- Google Chrome and ChromeDriver
- OpenAI API key

### Setup
```bash
git clone [repo-link]
cd JunkProspector
pip install -r requirements.txt
```

Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

## Usage

### Starting the Application
```bash
python app.py
```
Access the application at `http://localhost:5000`

### Running Scraper & Analysis
- Enter the auction start URL in the web interface.
- Click submit; the system automatically scrapes items, analyzes prices, and identifies bargains.

### Manual Execution
```bash
python JunkProspector.py [START_URL]
```

## Components
- `app.py`: Flask application and database manager.
- `JunkReader.py`: Scrapes auction item details.
- `JunkResearcher.py`: Performs item value analysis using Google search and OpenAI.
- `JunkCompare.py`: Compares auction prices to market estimates to identify bargains.
- `JunkProspector.py`: Concurrently runs scraping and analysis.

## Database Structure
- **Table:** `lot_items`
  - `id`: Item identifier
  - `name`: Item name
  - `current_bid`: Current auction bid
  - `description`: Item description
  - `url`: Item auction page URL
  - `analysis`: AI-generated market value analysis and bargain assessment
