"""Compare like-for-like KB area IDs; never compare schema-1 complex minima."""
def compare(previous, current, threshold=150000):
    baseline=bool(previous and previous.get('schema_version')==2)
    old={(r['complex_id'],r['area_id']):r for r in previous['items']} if baseline else {}
    result={'baseline_available':baseline,'previous_collected_at':previous.get('collected_at') if baseline else None,
        'current_collected_at':current['collected_at'],'threshold_manwon':threshold,'newly_below':[],'newly_available_below':[]}
    if not baseline:
        return result
    for row in current['items']:
        price=row.get('general_price_manwon')
        if row.get('price_status')!='kb_general' or price is None or price>threshold:
            continue
        prior=old.get((row['complex_id'],row['area_id']))
        old_price=prior.get('general_price_manwon') if prior and prior.get('price_status')=='kb_general' else None
        item={**row,'previous_price_manwon':old_price}
        if old_price is None:
            result['newly_available_below'].append(item)
        elif old_price>threshold:
            result['newly_below'].append(item)
    return result
