# Address Fixer

A Python utility for parsing and standardizing US postal addresses from various formats into a consistent structure.

## Overview

This tool takes addresses in various formats and normalizes them into a consistent structure with:

- Primary address (street number and name)
- Secondary address (suite/unit information)
- City
- State
- ZIP code

### Features

- Handles multiple address formats:
  - Comma-separated: "123 Main St, Suite 100, Portland, OR 97201"
  - Newline-separated: "123 Main St\nPortland, OR 97201"
  - Space-separated: "123 Main St Portland OR 97201"
- Extracts suite/unit information
- Formats 9-digit ZIP codes with hyphens
- Attempts to recover malformed addresses
- Separates valid and invalid addresses into different output files

## Processing Logic

The address parser follows these steps:

1. **Initial Cleanup**
   - Remove quotes and excess whitespace
   - Replace newlines with commas

2. **Basic Parsing**
   - Split on commas if present
   - Look for STATE ZIP pattern if no commas
   - Extract street address from beginning

3. **Unit/Suite Extraction**
   - Look for indicators like "STE", "SUITE", "APT", etc.
   - Separate unit info into address_line_2

4. **Validation and Recovery**
   - Format 9-digit ZIP codes (12345-6789)
   - Attempt to recover invalid addresses
   - Fix cases where city got mixed into address_line_2

## Usage

Input CSV must have a 'Location Address' column. The tool will create two output files:

- `valid_addresses.csv`: Successfully parsed addresses
- `invalid_addresses.csv`: Addresses that couldn't be parsed

### Example Input/Output

Input:

```
"123 Main St Suite 100 Portland, OR 97201"
"456 Oak Ave\nSalem, OR 97301"
"789 Pine St Portland OR 97204-1234"
```

Output:

```csv
address_line_1,address_line_2,city,state,zip
123 Main St,Suite 100,Portland,OR,97201
456 Oak Ave,,Salem,OR,97301
789 Pine St,,Portland,OR,97204-1234
```

## Requirements

- Python 3.6+
- pandas

## Installation

```bash
git clone https://github.com/yourusername/address-fixer.git
cd address-fixer
pip install -r requirements.txt
```

## Running the Tool

```bash
python -m address_fixer
```

## Error Handling

The tool handles common address format issues:

- Missing commas
- Extra whitespace
- Inconsistent suite/unit formatting
- Mixed newlines and commas
- Missing address components

Invalid addresses are written to a separate file for manual review.
