# Legislation Term Definition Generator

This script generates comprehensive definitions for legislation terms using Claude Sonnet API, based on legislative text and case law paragraphs.

## Setup

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API Key:**
   Create a `.env` file in the project root with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```
   
   Get your API key from: https://console.anthropic.com/

## Files

- `generate_definitions.py` - Main script that processes the CSV and generates definitions
- `prompt.txt` - Prompt template used for LLM requests
- `final_dataser_of_key_phrases.csv` - Input CSV file (must exist in project root)
- `requirements.txt` - Python dependencies

## Usage

Run the script:
```bash
python generate_definitions.py
```

## Output

The script generates:

1. **`legislation_term_definitions.csv`** - Final results with columns:
   - `legislation_id` - The legislation identifier
   - `legislation_term` - The term being defined
   - `legislation_term_definition` - The generated definition

2. **`llm_responses_YYYYMMDD_HHMMSS.log`** - Log file containing:
   - All prompts sent to the LLM
   - All responses received
   - Processing status and errors

3. **`definitions_intermediate_N.csv`** - Intermediate results saved every 10 groups (for recovery if script stops)

## How It Works

1. Reads `final_dataser_of_key_phrases.csv`
2. Groups rows by unique combinations of `legislation_term` and `legislation_id`
3. For each group:
   - Collects all `section_text` from the legislation
   - Collects all `paragraphs` from different case laws
   - Collects related `case_term` values
   - Sends a formatted prompt to Claude Sonnet API
   - Receives and stores the generated definition
4. Saves all results to CSV and logs all interactions

## Notes

- The script includes a 0.5 second delay between API calls to avoid rate limiting
- Intermediate results are saved every 10 groups for recovery
- All LLM interactions are logged for transparency and debugging
- For time being the code only process one term 
 --   change this line to  for (legislation_term, legislation_id), group_df in groups_list[:1]:
 --    for (legislation_term, legislation_id), group_df in groups_list: to process all of it 



