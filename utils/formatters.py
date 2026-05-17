# -- DATASET -> YFINANCE

quarter_to_month = {
    "Q1": "03",
    "Q2": "06",
    "Q3": "09",
    "Q4": "12"
}

company_to_ticker = {
    "Accenture": "ACN",
    "Adobe": "ADBE",
    "Airbus": "AIR.PA",
    "Allstate": "ALL",
    "Alphabet": "GOOGL",
    "Amadeus": "AMS.MC",
    "Amazon": "AMZN",
    "AMD": "AMD",
    "Apple": "AAPL",
    "AXP": "AXP",
    "BAM": "BAM",
    "Bank of America": "BAC",
    "BBVA": "BBVA.MC",
    "BKNG": "BKNG",
    "BMW": "BMW.DE",
    "BP": "BP.L",
    "Branco": "MDIA3.SA",
    "Capgemini": "CAP.PA",
    "Cardinal Health": "CAH",
    "Cisco": "CSCO",
    "Citi": "C",
    "Compass Group": "CPG.L",
    "Costco": "COST",
    "Deutsche Bank": "DBK.DE",
    "EDF": "EDF.PA",
    "Elevance Health": "ELV",
    "Engie": "ENGI.PA",
    "Ford": "F",
    "GM": "GM",
    "IBM": "IBM",
    "JPM": "JPM",
    "Loreal": "OR.PA",
    "Louis Vuitton": "LVMH.PA",
    "Lululemon": "LULU",
    "Marriott": "MAR",
    "Mastercard": "MA",
    "META": "META",
    "Microsoft": "MSFT",
    "Nike": "NKE",
    "Nvidia": "NVDA",
    "Oracle": "ORCL",
    "PAYPAL": "PYPL",
    "SalesForce": "CRM",
    "Schneider Electric": "SU.PA",
    "Shell": "SHEL.L",
    "SIE": "SIE.DE",
    "UnitedHealth": "UNH",
    "Volvo": "VOLV-B.ST",
    "Walmart": "WMT",
    "Walt Disney": "DIS",
}

# sees if the model's sentiment was reflected in the price return
def decide_accuracy(sentiment_score, price_return):
    if (sentiment_score > 0.5 and price_return < 0) or (sentiment_score < 0.5 and price_return > 0):
        return False
    else:
        return True
    