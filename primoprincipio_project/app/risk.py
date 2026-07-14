THRESHOLD = 106.8
def classify(current_dd, future_series):
    if current_dd >= THRESHOLD: return "red", "RISCHIO ALTO", "AGISCI"
    if any(day["cumulative"] >= THRESHOLD for day in future_series[:10]): return "yellow", "RISCHIO MEDIO", "SVEGLIATI"
    return "green", "RISCHIO ASSENTE", "DORMI"
