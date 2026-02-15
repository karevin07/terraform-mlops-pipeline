
import os
import argparse
import yfinance as yf
import boto3
import pandas as pd
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_upload(tickers, bucket, days=365):
    """
    Fetch historical data for multiple tickers and upload to S3 as a single CSV.
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    all_data = []

    for ticker in tickers:
        # Auto-append .TW for 4-digit codes if not present (simple heuristic for TW stocks)
        if len(ticker) == 4 and ticker.isdigit():
            ticker = f"{ticker}.TW"
            
        logger.info(f"Fetching data for {ticker} from {start_date.date()} to {end_date.date()}")
        try:
            df = yf.download(ticker, start=start_date, end=end_date)
            
            # Flatten MultiIndex columns if present (yfinance returning (Price, Ticker))
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                continue
                
            # Reset index to make Date a column
            df.reset_index(inplace=True)
            # Add Ticker column
            df['Ticker'] = ticker
            
            all_data.append(df)
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {ticker}: {e}")
            # Continue to next ticker even if one fails
            continue

    if not all_data:
        logger.error("No data fetched for any ticker.")
        return

    # Concatenate all data
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Save to CSV in memory
    csv_buffer = final_df.to_csv(index=False)
    
    try:
        # Upload to S3
        s3 = boto3.client('s3')
        key = "data.csv" # The training script expects this key
        
        logger.info(f"Uploading combined data to s3://{bucket}/{key}")
        s3.put_object(Bucket=bucket, Key=key, Body=csv_buffer)
        
        logger.info("Upload successful")
        
    except Exception as e:
        logger.error(f"Failed to upload data: {e}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch stock data and upload to S3")
    parser.add_argument("--tickers", type=str, nargs='+', required=True, help="List of stock ticker symbols (e.g., AAPL 2330 0050 QQQ)")
    parser.add_argument("--bucket", type=str, required=True, help="Target S3 bucket name")
    parser.add_argument("--days", type=int, default=365*2, help="Number of days of history to fetch")
    
    args = parser.parse_args()
    
    fetch_and_upload(args.tickers, args.bucket, args.days)
