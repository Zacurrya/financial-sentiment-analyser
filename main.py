from dotenv import load_dotenv
import os
from transformers import pipeline
from earning_call_transcripts import walk_dataset, chunk_transcript
from price_return import get_price_return
from utils.formatters import company_to_ticker, decide_accuracy
import csv
import pandas as pd

load_dotenv()

# import FinBERT data classification
classifier = pipeline("text-classification", model="ProsusAI/finbert", token=os.getenv("HF_TOKEN")) 

dataset_path = "C:/Users/zakyy/.cache/kagglehub/datasets/ramssvimala/earning-call-transcripts/versions/3/cleaned_ECTs_dataset"

# gets an overall sentiment score using the chunks
def get_sentiment_score(metadata):
    chunks = chunk_transcript(metadata["transcript"]) # chunk the transcript
    metadata.pop("transcript") # no longer needed

    scores = []
    for chunk in chunks:
        result = classifier(chunk, truncation=True, max_length=512)[0] # label: pos/neg/ntr, score: 0-1
        label = result["label"].lower()

        confidence = result["score"]
        
        if label == "positive": scores.append(confidence)
        elif label == "negative": scores.append(-confidence)
    
    price_return = sum(scores) / len(scores) if scores else 0 # accounts for edge case of entirely netural earnings call
    return price_return

# takes the metadata of an earnings call and adds it to the df
def write_to_csv(metadata):
    output_file = "results.csv"
    fieldnames = ["company", "year", "quarter", "sentiment_score", "price_return", "aligned"]

    # write header only if file doesn't exist
    write_header = not os.path.exists(output_file)
    
    # store results in a csv file
    with open(output_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header: writer.writeheader()
        writer.writerow(metadata)

if __name__ == '__main__':
    # get metadata for all earning call transcripts in the dataset
    results = walk_dataset(dataset_path)
    
    processed = set()
    if os.path.exists("results.csv"):
        existing = pd.read_csv("results.csv")
        processed = set(zip(existing["company"], existing["year"], existing["quarter"]))

    # loop through results, removing the transcript and enriching metadata with the price return, sentiment score, and if it held up
    for metadata in results:
        
        # skips duplicates
        key = (metadata["company"], metadata["year"], metadata["quarter"])
        if key in processed: continue

        # gets sentiment score and the price return over that period
        metadata["sentiment_score"] = get_sentiment_score(metadata) 
        metadata["price_return"] = get_price_return(
            company_to_ticker[metadata["company"]], 
            metadata["year"], 
            metadata["quarter"]
            )
        if metadata["price_return"] is None: continue

        # did the sentiment score reflect in the price return of that quarter?
        metadata["aligned"] = decide_accuracy(metadata["sentiment_score"], metadata["price_return"])

        write_to_csv(metadata)