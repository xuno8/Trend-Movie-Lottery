# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a **Trend Movie Lottery Draw** application built with Streamlit that processes CSV registration data and conducts lottery draws for movie tickets. The application handles preference-based lottery selection with cost tracking and violation detection.

## Commands

### Running the Application
```bash
streamlit run lottery.py
```

### Environment Setup
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

**Main Application (`lottery.py`)**: Single-file Streamlit application containing:
- CSV upload and validation
- Dynamic preference column detection (第一志願, 第二志願, etc.)
- Preference cleaning and duplicate detection
- Blacklist functionality for excluding specific email addresses
- Lottery algorithm with preference ordering
- Cost calculation and reporting
- Multi-sheet Excel export functionality

### Key Data Flow

1. **CSV Processing**: Reads uploaded CSV and dynamically detects preference columns
2. **Data Cleaning**: Removes duplicate preferences per user and tracks violations
3. **Blacklist Processing**: Parses blacklist input and filters out specified email addresses
4. **Lottery Selection**: Iterates through preference levels (1st choice → 2nd choice → etc.) and randomly selects winners within slot limits, excluding blacklisted users
5. **Results Export**: Generates Excel file with separate sheets for each option, losers, violations, and blacklisted users

### Required CSV Structure

The application expects CSV files with these columns:
- `Email`
- `Name` 
- `PSID`
- `登記票數 Number of tickets`
- `第一志願` (First preference)
- `第二志願` (Second preference)
- `第三志願` (Third preference)
- `第四志願` (Fourth preference)

### Key Functions

- `clean_preferences()` (line 40-50): Removes duplicate preferences and tracks violations
- Blacklist processing (lines 78-87): Parses and validates blacklist email addresses
- Blacklist filtering (lines 103-108): Removes blacklisted users from lottery pool
- Main lottery logic (lines 110-120): Preference-based selection algorithm
- Cost calculation and statistics (lines 124-138): Tracks total costs and blacklist statistics

### Blacklist Feature

The application includes a blacklist feature that allows excluding specific email addresses from the lottery:
- Input: One email address per line in the sidebar text area
- Processing: Validates email format, removes duplicates, converts to lowercase
- Effect: Blacklisted users are excluded from all lottery selection but tracked separately
- Output: Statistics and separate Excel sheet for blacklisted users

### Dependencies

Built on Streamlit with pandas for data processing, numpy for random selection, and openpyxl for Excel export functionality.