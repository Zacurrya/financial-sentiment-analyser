from pathlib import Path
from transformers import pipeline
import os

# import FinBERT data classification
classifier = pipeline("text-classification", model="ProsusAI/finbert", token=os.getenv("HF_TOKEN")) 

# extract and return company name, year and quarter
def parse_filepath(path):
    p = Path(path)
    company = p.parent.name
    stem = p.stem 
    parts = stem.split("_")
    year, quarter = parts[0], parts[1]
    metadata = {
        "company": company,
        "year": year,
        "quarter": quarter
    }
    return metadata

# rescursively add the metadata of each earnings call transcript to an array of metadata objects
def walk_dataset(dataset_path):
    results = []
    for txt_file in Path(dataset_path).rglob("*.txt"): # traverses through the dataset path using dfs to find any .txt files
        metadata = parse_filepath(txt_file)
        metadata["transcript"] = txt_file.read_text(encoding="utf-8") # adds transcript text to metadata
        results.append(metadata)
    return results

def chunk_transcript(text, max_tokens=400):
    sentences = text.split('. ')
    chunks = []
    current_chunk = []
    current_length = 0


    for sentence in sentences:
        token_estimate = len(sentence.split()) # rough word count for token estimate
        if current_length + token_estimate > max_tokens:
            chunks.append('. '.join(current_chunk))
            current_chunk = [sentence]
            current_length = token_estimate
        else:
            current_chunk.append(sentence)
            current_length += token_estimate
    
    if current_chunk:
        chunks.append('. '.join(current_chunk))
    
    return chunks

# gets an overall sentiment score from the transcript text
def get_sentiment_score(transcript):
    result = classifier(transcript, truncation=True, max_length=512)[0] # label: pos/neg/ntr, score: 0-1
    label = result["label"].lower()
    confidence = result["score"]

    if label == "positive":
        return confidence
    if label == "negative":
        return -confidence
    return 0
