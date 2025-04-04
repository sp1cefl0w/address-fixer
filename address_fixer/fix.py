import pandas as pd
from typing import List, Dict, Tuple
import os
import re
import logging
from datetime import datetime

# Add logging configuration at the top
log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'address_processing.log')
logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# This assumes your raw .csv file is in root.
_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_csv_filename = 'DQF Locations_ALL REGIONS_Waste Connections Apr 2 2025.csv'
_csv_path = os.path.join(_root_dir, _csv_filename)

# You can add to this if you find more 'address line 2' indicators in your dataset.
_unit_indicators = ['STE', 'SUITE', 'APT', 'UNIT', '#', 'FL', 'FLOOR']

def clean_address(addr: str) -> str:
    """Clean and standardize address string.
    
    Args:
        addr: Raw address string to clean.
        
    Returns:
        str: Cleaned address with standardized spacing and no quotes.
    """
    if not addr:
        return ''
    return ' '.join(addr.replace('"', '').split())

def extract_address_parts(street_part: str) -> Tuple[str, str]:
    """Separate address line 1 and 2 based on common identifiers.
    
    Args:
        street_part: Street address portion to parse.
        
    Returns:
        Tuple[str, str]: Tuple containing (address_line_1, address_line_2).
    """
    words = street_part.upper().split()
    
    for i, word in enumerate(words):
        if word in _unit_indicators:
            return ' '.join(words[:i]), ' '.join(words[i:])
    return street_part, ''

def format_zip(zip_code: str) -> str:
    """Format zip code to add hyphen for 9-digit codes.
    
    Args:
        zip_code: Raw zip code string to format.
        
    Returns:
        str: Formatted zip code with hyphen for 9-digit codes.
    """
    zip_clean = ''.join(c for c in zip_code if c.isdigit())
    
    # If it's a 9-digit zip, add the dash
    if len(zip_clean) == 9:
        return f"{zip_clean[:5]}-{zip_clean[5:]}"
    return zip_clean

def extract_unit(text: str) -> Tuple[str, str]:
    """Extract unit/suite information from text.
    
    Args:
        text: Address text to parse for unit information.
        
    Returns:
        Tuple[str, str]: Tuple containing (main_address, unit_info).
    """
    words = text.upper().split()
    
    for i, word in enumerate(words):
        if word in _unit_indicators:
            return ' '.join(words[:i]), ' '.join(words[i:])
    return text, ''

def validate_and_fix_addresses(valid_addresses: List[Dict]) -> List[Dict]:
    """Final validation to fix addresses and format zip codes.
    
    Args:
        valid_addresses: List of address dictionaries to validate.
        
    Returns:
        List[Dict]: List of validated and fixed address dictionaries.
    """
    
    logging.info("Starting address validation and fixes...")
    fixes_made = 0
    
    for addr in valid_addresses:
        original = addr.copy()
        changes = []
        
        # Fix zip code format
        if addr['zip']:
            old_zip = addr['zip']
            addr['zip'] = format_zip(addr['zip'])
            if old_zip != addr['zip']:
                changes.append(f"zip: {old_zip} -> {addr['zip']}")
        
        # Fix suite/city split in address_line_2
        if addr['address_line_2']:
            words = addr['address_line_2'].upper().split()
            if words[0] in _unit_indicators and len(words) > 1:
                # Find where unit info ends
                unit_end = 1
                if unit_end < len(words) and words[unit_end][0].isdigit():
                    unit_end += 1
                
                if unit_end < len(words):
                    old_addr2 = addr['address_line_2']
                    old_city = addr['city']
                    
                    # Move extra words to city
                    addr['city'] = ' '.join(words[unit_end:])
                    addr['address_line_2'] = ' '.join(words[:unit_end])
                    
                    changes.append(f"address_line_2: {old_addr2} -> {addr['address_line_2']}")
                    changes.append(f"city: {old_city} -> {addr['city']}")
        
        # Log changes if any were made
        if changes:
            fixes_made += 1
            logging.info(f"Fixed address {addr['source_index']}:")
            logging.info(f"Before: {original}")
            logging.info(f"After: {addr}")
            logging.info(f"Changes made: {', '.join(changes)}")
    
    logging.info(f"Validation complete - {fixes_made} addresses modified")
    return valid_addresses


def parse_addresses(addresses: List[str]) -> Tuple[List[Dict], List[Dict]]:
    """Parse addresses into components and separate valid and invalid addresses.
    
    Args:
        addresses: List of raw address strings to parse.
        
    Returns:
        Tuple[List[Dict], List[Dict]]: Tuple containing (valid_addresses, invalid_addresses).
            Each address is a dictionary with keys:
            - source_index: Original index in input list
            - address_line_1: Primary street address
            - address_line_2: Suite/unit information
            - city: City name
            - state: Two-letter state code
            - zip: ZIP code
    """
    valid_addresses = []
    invalid_addresses = []
    
    for idx, address in enumerate(addresses):
        logging.info(f"Processing address index {idx}: {address}")
        
        if not address or not address.strip():
            logging.warning(f"Empty address at index {idx}")
            invalid_addresses.append({'source_index': idx, 'invalid_address': address})
            continue
            
        try:
            # First replace newlines with commas and clean whitespace
            cleaned = address.replace('"', '').replace('\n', ',')
            cleaned = ' '.join(cleaned.split())
            logging.debug(f"Cleaned address: {cleaned}")
            
            # Split on commas
            parts = [p.strip() for p in cleaned.split(',')]
            logging.debug(f"Split parts: {parts}")
            
            if len(parts) >= 2:  # Has at least one comma
                street = parts[0]
                remainder = ','.join(parts[1:])
            else:
                # No commas - look for state pattern
                words = cleaned.split()
                for i, word in enumerate(words):
                    if len(word) == 2 and word.isalpha():
                        street = ' '.join(words[:i-1])
                        remainder = ' '.join(words[i-1:])
                        break
                else:
                    raise ValueError("Could not find state")
            
            # Parse city, state, zip from remainder
            if ',' in remainder:
                city, state_zip = [p.strip() for p in remainder.rsplit(',', 1)]
            else:
                words = remainder.split()
                for i, word in enumerate(words):
                    if len(word) == 2 and word.isalpha():
                        city = ' '.join(words[:i])
                        state_zip = ' '.join(words[i:])
                        break
                else:
                    raise ValueError("Could not find state")
            
            # Look for unit/suite in street part
            addr_line1 = street
            addr_line2 = ''
            words = street.upper().split()
            for i, word in enumerate(words):
                if word in _unit_indicators:
                    addr_line1 = ' '.join(words[:i])
                    addr_line2 = ' '.join(words[i:])
                    break
            
            state_zip_parts = state_zip.strip().split()
            if len(state_zip_parts) == 2:
                parsed = {
                    'source_index': idx,
                    'address_line_1': addr_line1,
                    'address_line_2': addr_line2,
                    'city': city.strip('"').strip(','),
                    'state': state_zip_parts[0],
                    'zip': state_zip_parts[1]
                }
                logging.info(f"Successfully parsed address {idx}: {parsed}")
                valid_addresses.append(parsed)
                continue
            
            logging.warning(f"Could not parse address {idx}: {cleaned}")
            invalid_addresses.append({'source_index': idx, 'invalid_address': cleaned})
            
        except Exception as e:
            logging.error(f"Error processing address {idx}: {str(e)}")
            invalid_addresses.append({'source_index': idx, 'invalid_address': address})
    
    return valid_addresses, invalid_addresses

def recover_invalid_addresses(invalid_addresses: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """Attempt to recover invalid addresses using simpler parsing rules.
    
    Args:
        invalid_addresses: List of invalid address dictionaries to attempt to recover.
        
    Returns:
        Tuple[List[Dict], List[Dict]]: Tuple containing (recovered_addresses, still_invalid_addresses).
    """
    logging.info("Attempting to recover invalid addresses...")
    recovered = []
    still_invalid = []
    
    for invalid in invalid_addresses:
        try:
            addr = invalid['invalid_address']
            if not addr or not addr.strip():
                still_invalid.append(invalid)
                continue
                
            # Log recovery attempt
            logging.info(f"Attempting to recover address: {addr}")
            
            words = addr.upper().strip().split()
            for i, word in enumerate(words):
                if (len(word) == 2 and word.isalpha() and 
                    i + 1 < len(words) and words[i+1].isdigit()):
                    # Found state and zip pattern
                    recovered_addr = {
                        'source_index': invalid['source_index'],
                        'address_line_1': ' '.join(words[:i-1]),
                        'address_line_2': '',
                        'city': words[i-1],
                        'state': word,
                        'zip': words[i+1]
                    }
                    
                    logging.info(f"Successfully recovered address {invalid['source_index']}:")
                    logging.info(f"From: {addr}")
                    logging.info(f"To: {recovered_addr}")
                    
                    recovered.append(recovered_addr)
                    break
            else:
                logging.warning(f"Could not recover address {invalid['source_index']}: {addr}")
                still_invalid.append(invalid)
                
        except Exception as e:
            logging.error(f"Error recovering address {invalid['source_index']}: {str(e)}")
            still_invalid.append(invalid)
    
    logging.info(f"Recovery complete - {len(recovered)} addresses recovered")
    return recovered, still_invalid

def process_invalid_addresses(invalid_records: List[Dict]) -> List[Dict]:
    """Process invalid addresses using basic parsing rules.
    
    Args:
        invalid_records: List of invalid address records to process.
        
    Returns:
        List[Dict]: List of successfully recovered address dictionaries.
    """
    recovered = []
    
    for record in invalid_records:
        try:
            addr = record['invalid_address']
            if not addr or not addr.strip():
                continue
                
            # Clean and split on spaces
            words = addr.strip().upper().split()
            
            # Look for state pattern (2 letters + zip)
            for i, word in enumerate(words):
                if (len(word) == 2 and word.isalpha() and 
                    i + 1 < len(words) and words[i+1].isdigit()):
                    # Found state and zip - work backwards
                    state = word
                    zip_code = words[i+1]
                    city = words[i-1]  # Word before state is city
                    street = ' '.join(words[:i-1])  # Everything before is street
                    
                    recovered.append({
                        'source_index': record['source_index'],
                        'address_line_1': street,
                        'address_line_2': '',
                        'city': city,
                        'state': state,
                        'zip': zip_code
                    })
                    break
                    
        except Exception as e:
            continue
    
    return recovered

def main():
    """Main entry point for address processing.
    
    Reads addresses from CSV, processes them through parsing and validation,
    attempts to recover invalid addresses, and writes results to output files.
    
    Input file must have a 'Location Address' column.
    Outputs:
        - valid_addresses.csv: Successfully parsed addresses
        - invalid_addresses.csv: Addresses that could not be parsed
    """
    logging.info("="*80)
    logging.info(f"Starting address processing at {datetime.now()}")
    
    try:
        # Read addresses from CSV file
        df = pd.read_csv(_csv_path, dtype={'Location Address': str})
        logging.info(f"Read {len(df)} addresses from {_csv_path}")
        if 'Location Address' not in df.columns:
            print("Error: CSV file must contain a 'Location Address' column")
            return
        
        # Convert any null values to empty strings
        df['Location Address'] = df['Location Address'].fillna('')
        addresses = df['Location Address'].tolist()
        valid, invalid = parse_addresses(addresses)
        
        # Create DataFrames
        valid_df = pd.DataFrame(valid)
        invalid_df = pd.DataFrame(invalid)
        
        # Sort by source index
        valid_df = valid_df.sort_values('source_index')
        
        # Apply validation and fixes - THIS IS THE KEY CHANGE
        valid_records = validate_and_fix_addresses(valid_df.to_dict('records'))
        valid_df = pd.DataFrame(valid_records)
        
        # Process invalid addresses
        recovered_records = process_invalid_addresses(invalid_df.to_dict('records'))
        
        # Add recovered records to valid_df
        if recovered_records:
            recovered_df = pd.DataFrame(recovered_records)
            valid_df = pd.concat([valid_df, recovered_df])
            
            # Sort by source index again
            valid_df = valid_df.sort_values('source_index')
        
        # Export to CSV
        valid_df.to_csv(os.path.join(_root_dir, 'valid_addresses.csv'), index=False)
        # Only write truly invalid addresses to invalid CSV
        still_invalid = [r for r in invalid_df.to_dict('records') 
                        if r['source_index'] not in valid_df['source_index'].values]
        pd.DataFrame(still_invalid).to_csv(os.path.join(_root_dir, 'invalid_addresses.csv'), index=False)
        
        pd.DataFrame(still_invalid).to_csv(os.path.join(_root_dir, 'invalid_addresses.csv'), index=False)

        logging.info(f"Processing complete:")
        logging.info(f"Total addresses processed: {len(addresses)}")
        logging.info(f"Valid addresses: {len(valid_df)}")
        logging.info(f"Invalid addresses: {len(still_invalid)}")
        logging.info(f"Recovered addresses: {len(recovered_records)}")
        logging.info("="*80)
        
        print(f"\nProcessed {len(addresses)} addresses")
        print(f"Valid: {len(valid_df)}")
        print(f"Invalid: {len(still_invalid)}")
        print(f"Recovered from invalid: {len(recovered_records)}")
        
    except FileNotFoundError:
        print(f"Error: Could not find CSV file at {_csv_path}")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    main()