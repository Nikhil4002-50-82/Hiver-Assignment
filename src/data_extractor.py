
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
    if not text:
        return ""
    cleaned = re.sub(r"@\d+", "", text)
    cleaned = re.sub(r"@British_Airways", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def extract_british_airways_conversations(
    raw_csv_path: Path = RAW_DATA_FILE,
    output_csv_path: Path = CONVERSATION_PAIRS_FILE,
    max_pairs: int = 25000
) -> int:
    if not raw_csv_path.exists():
        raise FileNotFoundError(f"Raw dataset not found at: {raw_csv_path}")

    print(f"--> Starting extraction from {raw_csv_path}...")
    
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

            if author.lower() == TARGET_BRAND_NAME.lower() and not inbound:
                if in_response_to:
                    ba_replies[in_response_to] = {
                        "agent_tweet_id": tweet_id,
                        "agent_reply": text,
                        "created_at": created_at
                    }

            elif inbound and ("british_airways" in text.lower() or "british airways" in text.lower()):
                customer_tweets[tweet_id] = {
                    "customer_tweet_id": tweet_id,
                    "customer_text": text,
                    "created_at": created_at
                }

    print(f"--> Extraction pass 1 complete:")
    print(f"    Total BA replies found: {len(ba_replies):,}")
    print(f"    Total Inbound customer tweets found: {len(customer_tweets):,}")

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

    paired_rows: List[Dict[str, str]] = []
    for parent_tweet_id, reply_data in ba_replies.items():
        if parent_tweet_id in customer_tweets:
            cust_data = customer_tweets[parent_tweet_id]
            clean_cust_text = clean_tweet_text(cust_data["customer_text"])
            clean_reply_text = clean_tweet_text(reply_data["agent_reply"])

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
