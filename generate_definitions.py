"""
Script to generate definitions for legislation terms using Claude Sonnet API.
Reads final_dataser_of_key_phrases.csv, groups by legislation_term and legislation_id,
and generates definitions based on section_text and case law paragraphs.
"""

import os
import pandas as pd
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
import time

# Load environment variables
load_dotenv()

# Configure logging
log_filename = f"llm_responses_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Anthropic client
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in .env file. Please add it.")

client = Anthropic(api_key=api_key)

# Read the prompt template
def load_prompt_template():
    """Load the prompt template from prompt.txt"""
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error("prompt.txt file not found!")
        raise


def format_case_law_paragraphs(group_df):
    """
    Format case law paragraphs for the prompt.
    Groups paragraphs by case law URL and includes para_id.
    """
    paragraphs_list = []
    for idx, row in group_df.iterrows():
        url = row.get('url', 'Unknown URL')
        para_id = row.get('para_id', 'Unknown')
        paragraph = row.get('paragraphs', '')
        
        if pd.notna(paragraph) and paragraph.strip():
            paragraphs_list.append(f"Case Law: {url} (Paragraph: {para_id})\n{paragraph}\n")
    
    return "\n---\n\n".join(paragraphs_list)


def get_case_terms(group_df):
    """
    Extract unique case terms from the group.
    """
    case_terms = group_df['case_term'].dropna().unique().tolist()
    return ", ".join(case_terms) if case_terms else "None identified"


def call_claude_sonnet(prompt_text):
    """
    Call Claude Sonnet API with the prompt and return the response.
    """
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[
                {"role": "user", "content": prompt_text}
            ]
        )
        
        # Extract text from response
        response_text = ""
        for content_block in message.content:
            if content_block.type == "text":
                response_text += content_block.text
        
        return response_text.strip()
    
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        raise


def process_group(legislation_term, legislation_id, group_df, prompt_template):
    """
    Process a single group of rows (same legislation_term and legislation_id).
    """
    logger.info(f"Processing: {legislation_term} ({legislation_id})")
    
    # Get section_text (should be the same for all rows in group, take first non-null)
    section_text = group_df['section_text'].dropna().iloc[0] if not group_df['section_text'].dropna().empty else ""
    
    # Format case law paragraphs
    case_law_paragraphs = format_case_law_paragraphs(group_df)
    
    # Get case terms
    case_terms = get_case_terms(group_df)
    
    # Fill in the prompt template
    prompt = prompt_template.format(
        legislation_term=legislation_term,
        legislation_id=legislation_id,
        section_text=section_text,
        case_law_paragraphs=case_law_paragraphs,
        case_terms=case_terms
    )
    
    # Log the prompt (for debugging)
    logger.info(f"Prompt length: {len(prompt)} characters")
    logger.info(f"Number of case law paragraphs: {len(group_df)}")
    
    # Call Claude API
    try:
        definition = call_claude_sonnet(prompt)
        
        # Log the response
        logger.info(f"Definition received (length: {len(definition)} characters)")
        logger.info(f"Response preview: {definition[:200]}...")
        
        # Log full interaction to file
        logger.info(f"\n{'='*80}")
        logger.info(f"Legislation Term: {legislation_term}")
        logger.info(f"Legislation ID: {legislation_id}")
        logger.info(f"\nPrompt:\n{prompt[:500]}...")
        logger.info(f"\nResponse:\n{definition}")
        logger.info(f"{'='*80}\n")
        
        return definition
    
    except Exception as e:
        logger.error(f"Failed to get definition for {legislation_term} ({legislation_id}): {str(e)}")
        return None


def main():
    """
    Main function to process the CSV and generate definitions.
    """
    logger.info("Starting definition generation process...")
    
    # Load prompt template
    prompt_template = load_prompt_template()
    logger.info("Prompt template loaded successfully")
    
    # Read the CSV file
    csv_file = 'final_dataser_of_key_phrases.csv'
    logger.info(f"Reading CSV file: {csv_file}")
    
    try:
        df = pd.read_csv(csv_file, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        logger.warning("UTF-8 encoding failed, trying latin-1...")
        df = pd.read_csv(csv_file, encoding='latin-1', low_memory=False)
    
    logger.info(f"Loaded {len(df)} rows from CSV")
    
    # Group by legislation_term and legislation_id
    logger.info("Grouping by legislation_term and legislation_id...")
    grouped = df.groupby(['legislation_term', 'legislation_id'])
    
    total_groups = len(grouped)
    logger.info(f"Found {total_groups} unique combinations of legislation_term and legislation_id")
    
    # Process each group
    results = []
    processed = 0
    
    # Convert grouped to list for iteration (can't slice GroupBy object directly)
    groups_list = list(grouped)
    # For testing: process only the first group
    for (legislation_term, legislation_id), group_df in groups_list[:1]:
        processed += 1
        logger.info(f"\nProcessing group {processed}/{total_groups}")
        
        # Process the group
        definition = process_group(legislation_term, legislation_id, group_df, prompt_template)
        
        # Store result
        results.append({
            'legislation_id': legislation_id,
            'legislation_term': legislation_term,
            'legislation_term_definition': definition if definition else "Error: Could not generate definition"
        })
        
        # Add a small delay to avoid rate limiting
        time.sleep(0.5)
        
        # Save intermediate results every 10 groups
        if processed % 10 == 0:
            intermediate_df = pd.DataFrame(results)
            intermediate_file = f"definitions_intermediate_{processed}.csv"
            intermediate_df.to_csv(intermediate_file, index=False, encoding='utf-8')
            logger.info(f"Saved intermediate results to {intermediate_file}")
    
    # Create final results DataFrame
    results_df = pd.DataFrame(results)
    
    # Save to CSV
    output_file = 'legislation_term_definitions.csv'
    results_df.to_csv(output_file, index=False, encoding='utf-8')
    logger.info(f"\nCompleted! Results saved to {output_file}")
    logger.info(f"Total definitions generated: {len(results_df)}")
    logger.info(f"Log file: {log_filename}")
    
    # Print summary
    successful = results_df['legislation_term_definition'].str.contains('Error', na=False).sum()
    logger.info(f"Successful definitions: {len(results_df) - successful}")
    logger.info(f"Failed definitions: {successful}")


if __name__ == "__main__":
    main()

