import pandas as pd

df = pd.read_csv("results.csv")

# overall alignment rate
alignment_rate = df["aligned"].mean() # True/False = 1/0

# correlation between sentiment score and price return
correlation = df["sentiment_score"].corr(df["price_return"])

# print results
print(f'The alignment rate of the sentiment score being indicitive of price movement for the following quarter was: {alignment_rate:.2%}') # to 2 s.f %
print(f'And the correlation between the sentiment score and price return (of the following quarter) was: {correlation:.2f}') # to 2 s.f
