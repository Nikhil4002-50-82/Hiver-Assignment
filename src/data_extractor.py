"""
Data Extractor for British Airways Support Conversations.

This script reads the large Kaggle customer support dataset (twcs.csv),
filters all conversations involving @British_Airways, pairs each customer
inbound tweet with the corresponding British Airways agent resolution,
and saves the clean conversation pairs into a lightweight CSV file.
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple
from src.config import (
    RAW_DATA_FILE, 
    CONVERSATION_PAIRS_FILE, 
    TARGET_BRAND_NAME, 
    PROCESSED_DATA_DIRECTORY
)


def clean_tweet_text(text: str) -> str:
    """
    Cleans raw tweet text by removing anonymized handles (like @115712) 
    and extra whitespace while preserving the core message.
    """
    if not text:
        return ""
    # Remove anonymized numeric handles like @115712 or brand handles like @British_Airways at start
    cleaned = re.sub(r"@\d+", "", text)
    cleaned = re.sub(r"@British_Airways", "", cleaned, flags=re.IGNORECASE)
    # Remove multiple spaces/newlines
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_british_airways_conversations(
    raw_csv_path: Path = RAW_DATA_FILE,
    output_csv_path: Path = CONVERSATION_PAIRS_FILE,
    max_pairs: int = 25000
) -> int:
    """
    Scans twcs.csv, extracts British Airways agent replies,
    matches them with incoming customer tweets, and writes out the pairs.
    """
    if not raw_csv_path.exists():
        raise FileNotFoundError(f"Raw dataset not found at: {raw_csv_path}")

    print(f"--> Starting extraction from {raw_csv_path}...")
    
    # Store BA replies: mapping in_response_to_tweet_id -> ba_reply_tweet
    # Also store customer tweets: mapping tweet_id -> customer_tweet
    ba_replies: Dict[str, Dict[str, str]] = {}
    customer_tweets: Dict[str, Dict[str, str]] = {}

    total_rows_scanned = 0
    
    with open(raw_csv_path, mode="r", encoding="utf-8", errors="ignore") as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            total_rows_scanned += 1
            if total_rows_scanned % 500000 == 0:
                print(f"    Scanned {total_rows_scanned:,} rows...")

            author = row.get("author_id", "")
            inbound = row.get("inbound", "").lower() == "true"
            tweet_id = row.get("tweet_id", "")
            in_response_to = row.get("in_response_to_tweet_id", "")
            text = row.get("text", "")
            created_at = row.get("created_at", "")

            # 1. Capture British Airways agent replies
            if author.lower() == TARGET_BRAND_NAME.lower() and not inbound:
                if in_response_to:
                    ba_replies[in_response_to] = {
                        "agent_tweet_id": tweet_id,
                        "agent_reply": text,
                        "created_at": created_at
                    }

            # 2. Capture potential customer tweets mentioning British Airways
            elif inbound and ("british_airways" in text.lower() or "british airways" in text.lower()):
                customer_tweets[tweet_id] = {
                    "customer_tweet_id": tweet_id,
                    "customer_text": text,
                    "created_at": created_at
                }

    print(f"--> Extraction pass 1 complete:")
    print(f"    Total BA replies found: {len(ba_replies):,}")
    print(f"    Total Inbound customer tweets found: {len(customer_tweets):,}")

    # If some customer tweets were not captured by text search, do a quick targeted pass
    # for missing in_response_to IDs that BA replied to
    missing_customer_ids = set(ba_replies.keys()) - set(customer_tweets.keys())
    if missing_customer_ids:
        print(f"--> Targeted pass for {len(missing_customer_ids):,} parent customer tweets...")
        with open(raw_csv_path, mode="r", encoding="utf-8", errors="ignore") as file:
            reader = csv.DictReader(file)
            for row in reader:
                tweet_id = row.get("tweet_id", "")
                if tweet_id in missing_customer_ids:
                    customer_tweets[tweet_id] = {
                        "customer_tweet_id": tweet_id,
                        "customer_text": row.get("text", ""),
                        "created_at": row.get("created_at", "")
                    }
                    missing_customer_ids.remove(tweet_id)
                    if not missing_customer_ids:
                        break

    # Pair customer tweets with BA replies
    paired_rows: List[Dict[str, str]] = []
    for parent_tweet_id, reply_data in ba_replies.items():
        if parent_tweet_id in customer_tweets:
            cust_data = customer_tweets[parent_tweet_id]
            clean_cust_text = clean_tweet_text(cust_data["customer_text"])
            clean_reply_text = clean_tweet_text(reply_data["agent_reply"])

            # Filter out very short or empty messages
            if len(clean_cust_text) >= 15 and len(clean_reply_text) >= 15:
                paired_rows.append({
                    "customer_tweet_id": cust_data["customer_tweet_id"],
                    "agent_tweet_id": reply_data["agent_tweet_id"],
                    "customer_text": clean_cust_text,
                    "agent_reply": clean_reply_text,
                    "created_at": reply_data["created_at"]
                })
                if len(paired_rows) >= max_pairs:
                    break

    # Write out the clean paired dataset
    output_csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["customer_tweet_id", "agent_tweet_id", "customer_text", "agent_reply", "created_at"]
    
    with open(output_csv_path, mode="w", encoding="utf-8", newline="") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(paired_rows)

    print(f"[SUCCESS] Successfully paired and saved {len(paired_rows):,} conversations to:")
    print(f"          {output_csv_path}")
    return len(paired_rows)


if __name__ == "__main__":
    extract_british_airways_conversations()
