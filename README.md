# NFL 2023 Data Explorer

A natural language interface for exploring 2023 NFL team statistics. Built for CS 3960 at the University of Utah.

## What it does

This tool lets users ask questions about NFL team stats in plain English and get instant answers as charts and tables — no coding or SQL knowledge required. It also shows the equivalent SQL query for each result so users can see how their question maps to a real database query.

## Features

- Natural language query input
- Bar charts for ranking queries (e.g. "which teams scored the most points")
- Scatter plots for comparison queries (e.g. "passing yards vs points scored")
- Two interpretations side by side with user feedback buttons
- Click to remove teams from charts
- Equivalent SQL query shown for every result

## How to run it

**1. Clone the repo**
```
git clone https://github.com/YOUR_USERNAME/nfl-data-explorer
cd nfl-data-explorer
```

**2. Install dependencies**
```
pip install streamlit pandas matplotlib numpy
```

**3. Run the app**
```
streamlit run nfl_explorer.py
```

The app will open in your browser at http://localhost:8501

## Example queries to try

- Which teams scored the most points?
- Show the top 10 rushing offenses
- Worst passing defense
- Who threw the most interceptions?
- Compare passing yards vs points scored
- Rushing yards vs points allowed

## Data

The dataset is `NFL_Combined_Data_2023.csv` which contains combined offensive and defensive stats for all 32 NFL teams from the 2023 regular season. Data sourced from Pro Football Reference.

## Project info

- Course: CS 3960 — Human Centered Data Management
- Author: David Perry — University of Utah
