TTH = 8.0
def hourly_to_daily_series(times, temps):
    buckets = {}
    for t, v in zip(times, temps):
        buckets.setdefault(t[:10], []).append(v)
    out = []
    cumulative = 0.0
    for d in sorted(buckets):
        vals = buckets[d]
        tmean = sum(vals)/len(vals) if vals else 0.0
        dd = max(0.0, tmean - TTH)
        cumulative += dd
        out.append({"date": d, "tmean": round(tmean,2), "dd": round(dd,2), "cumulative": round(cumulative,2)})
    return out
