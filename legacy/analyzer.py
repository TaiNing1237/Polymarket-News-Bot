import json
import logging
import os
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

class PolymarketAnalyzer:
    def __init__(self, arbitrage_threshold: float = 0.03):
        """
        :param arbitrage_threshold: The acceptable deviation from 1.0 for the sum of mutually exclusive outcomes.
                                    e.g., if sum of prices < (1 - 0.03) = 0.97, it's considered an arbitrage op.
        """
        self.arbitrage_threshold = arbitrage_threshold
        # Keep a basic history of prices to detect volatility if we run continuously
        # Structure: {market_id: {"last_price": [prices], "timestamp": ...}}
        self.price_history = {}
        
        # File to persist paper trade records
        self.paper_trade_log_file = "paper_trades.json"
        self._load_paper_trades()

    def _load_paper_trades(self):
        if os.path.exists(self.paper_trade_log_file):
            try:
                with open(self.paper_trade_log_file, "r", encoding="utf-8") as f:
                    self.paper_trades = json.load(f)
            except Exception as e:
                logger.error(f"Error loading paper trades: {e}")
                self.paper_trades = []
        else:
            self.paper_trades = []

    def save_paper_trade(self, trade_record: Dict):
        self.paper_trades.append(trade_record)
        try:
            with open(self.paper_trade_log_file, "w", encoding="utf-8") as f:
                json.dump(self.paper_trades, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving paper trade: {e}")

    def analyze_markets(self, markets: List[Dict]) -> List[Dict]:
        """
        Analyze a list of markets for inefficiencies or arbitrage.
        Returns a list of 'alerts' (opportunities found).
        """
        alerts = []
        
        for market in markets:
            market_id = market.get("id")
            question = market.get("question", "Unknown")
            event_slug = market.get("event_slug", "")
            outcomes = market.get("outcomes", [])
            
            # The API sometimes represents outcomePrices as strings "0.45", "0.55"
            raw_prices = market.get("outcomePrices", [])
            
            # Only process if valid outcomes and prices exist
            if not outcomes or not raw_prices or len(outcomes) != len(raw_prices):
                continue
                
            try:
                prices = [float(p) for p in raw_prices]
            except ValueError:
                continue # Skip if parsing fails
            
            # 1. Mutually Exclusive Arbitrage Check
            # Assuming these outcomes are mutually exclusive if it's a standard Yes/No or scalar market 
            # (Note: Multi-market events might have mutually exclusive markets, here we just sum outcomes in a single market)
            prob_sum = sum(prices)
            
            # Let's check for Yes/No first or any market where the sum should theoretically be 1.0
            # If sum < (1 - threshold), we might be able to buy all sides for < 100% and get 100% payout.
            lower_bound = 1.0 - self.arbitrage_threshold
            upper_bound = 1.0 + self.arbitrage_threshold # High sum means taking 'No' on all might be profitable if supported
            
            if prob_sum > 0 and (prob_sum < lower_bound or prob_sum > upper_bound):
                # We found an inefficiency
                alert = {
                    "type": "Arbitrage/Inefficiency",
                    "market_id": market_id,
                    "question": question,
                    "event_slug": event_slug,
                    "outcomes": outcomes,
                    "prices": prices,
                    "sum": round(prob_sum, 4),
                    "timestamp": datetime.now().isoformat(),
                    "link": f"https://polymarket.com/event/{event_slug}" if event_slug else "N/A"
                }
                alerts.append(alert)
                
                # Auto record paper trade for demonstration
                if prob_sum < lower_bound:
                    self.save_paper_trade({
                        "action": "BUY_ALL_SIDES",
                        "reason": "Sum of probabilities is too low",
                        **alert
                    })
                    
            # 2. Volatility / New Information Check 
            # (Checking for large price swings between current fetch and history)
            if market_id in self.price_history:
                old_prices = self.price_history[market_id]["prices"]
                for i, (new_p, old_p) in enumerate(zip(prices, old_prices)):
                    if abs(new_p - old_p) > 0.1: # 10% swing in a polling interval is huge
                        alerts.append({
                            "type": "Volatility Alert",
                            "market_id": market_id,
                            "question": question,
                            "outcome": outcomes[i],
                            "old_price": old_p,
                            "new_price": new_p,
                            "timestamp": datetime.now().isoformat(),
                            "link": f"https://polymarket.com/event/{event_slug}" if event_slug else "N/A"
                        })
            
            # Update history
            self.price_history[market_id] = {
                "prices": prices,
                "timestamp": datetime.now().isoformat()
            }
            
        return alerts

if __name__ == "__main__":
    from polymarket_api import PolymarketAPI
    api = PolymarketAPI()
    markets = api.extract_markets_from_events(api.get_active_events(limit=50))
    
    analyzer = PolymarketAnalyzer(arbitrage_threshold=0.03)
    alerts = analyzer.analyze_markets(markets)
    
    print(f"Analyzed {len(markets)} markets. Found {len(alerts)} alerts.")
    for a in alerts[:5]:
        print(json.dumps(a, indent=2, ensure_ascii=False))
