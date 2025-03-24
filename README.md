# JunkSniper
JunkSniper is an automated tool designed for bargain hunters, car boot buyers, and auction enthusiasts. It sifts through seemingly worthless auction junk to find hidden treasures utomatically cross-referencing auction listings against real-time market values, highlighting bargains priced significantly below their true worth.

# Key Features

Automatic Item Analysis:
Quickly scans auction listings, automating searches to discover hidden value.

Smart Price Comparison:
Integrates with Google to evaluate the real-world value of items.

Configurable Exclusions:
Optionally excludes specified websites (e.g., easyliveauctions, southdublinauction) to ensure accurate comparisons.

Flexible Valuation Logic:
Designed to handle a variety of items, adjusting analysis dynamically based on available comparable data.

Inline Real-time Checks:
Performs instant valuation during browsing, streamlining your treasure hunt.

Getting Started

Installation

Clone the repository:

git clone [your_repository_link]

Navigate into the project directory:

`cd junksniper`

Install required dependencies:

`pip install -r requirements.txt`

Set your OpemAI API Key as the following ENV variable

`OPENAI_API_KEY`

Set the base website URL and the URL of LOT #1 here:
`BASE_URL`
`START_URL`

Usage

Run the script using:

`python junksniper.py`

Configuration options (e.g., excluded websites, bargain thresholds) can be adjusted directly within the script.

Upcoming Features

Support for a broader range of auction websites.

Enhanced database integration for item tracking.

Enhanced LLM integration

User-friendly web interface.

Contribution
