# Brainstorming Project

## Data Handling
- **Never load GBs of data into memory at once**: The ChatGPT transaction parquet files are large. Process in chunks, sample first, or use lazy loading. A past instance crashed by loading too much data.
- Data lives in `/Users/jeffreyohl/Dropbox/Gambling Papers and Data/CEdge data`
- Main data loader: `load_chatgpt_data.py`

## Current Work
- Panelization of ChatGPT transaction data (in progress)
