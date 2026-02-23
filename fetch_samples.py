from polymarket_api import PolymarketAPI

api = PolymarketAPI()
events = api.get_active_events(limit=5)
markets = api.extract_markets_from_events(events)

import sys

with open('samples.txt', 'w', encoding='utf-8') as f:
    f.write("===== 市場總覽 =====\n")
    for m in markets[:10]:
        outcomes = m.get('outcomes', [])
        raw_prices = m.get('outcomePrices', "[]")
        if isinstance(raw_prices, str) and raw_prices.startswith('['):
            import json
            try:
                raw_prices = json.loads(raw_prices)
            except:
                raw_prices = []
        prices = [float(p) for p in raw_prices]
        f.write(f"事件: {m.get('event_title')}\n")
        f.write(f"問題: {m.get('question')}\n")
        f.write("賠率: " + ', '.join(f"{o}: {p*100:.1f}%" for o, p in zip(outcomes, prices)) + "\n")
        f.write('-'*40 + "\n")
