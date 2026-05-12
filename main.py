import os
from transformers import pipeline

# import FinBERT data classification
classifier = pipeline("text-classification", model="ProsusAI/finbert", token=os.getenv("HF_TOKEN")) 

sample = "Revenue exceeded expectations and margins improved significantly. Gross profit has raised 21% YOY however operations costs have risen 10% YOY."
result = classifier(sample)

print(result)