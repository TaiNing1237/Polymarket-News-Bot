import requests
import logging
import json
from typing import List, Dict

logger = logging.getLogger(__name__)

class PolymarketAPI:
    BASE_URL = "https://gamma-api.polymarket.com"

    def __init__(self):
        self.session = requests.Session()
        # Add a realistic User-Agent to avoid being blocked if they use basic Cloudflare rules
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json"
        })

    def get_active_events(self, limit: int = 100) -> List[Dict]:
        """
        Fetch active events from Gamma API.
        Events contain one or more markets.
        """
        endpoint = f"{self.BASE_URL}/events"
        params = {
            "active": "true",
            "closed": "false",
            "limit": limit
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data
        except Exception as e:
            logger.error(f"Failed to fetch active events: {e}")
            return []

    def extract_markets_from_events(self, events: List[Dict]) -> List[Dict]:
        """
        Extract all markets from a list of events.
        """
        all_markets = []
        for event in events:
            markets = event.get("markets", [])
            for market in markets:
                # enrich market data with event context
                market["event_title"] = event.get("title", "Unknown Event")
                market["event_slug"] = event.get("slug", "")
                all_markets.append(market)
        return all_markets

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    api = PolymarketAPI()
    events = api.get_active_events(limit=5)
    markets = api.extract_markets_from_events(events)
    print(f"Fetched {len(events)} events and {len(markets)} markets.")
    
    if markets:
        # Pring the first market structure to verify it
        print("\nSample Market structure:")
        sample = markets[0]
        # remove description to keep it clean
        if "description" in sample:
            del sample["description"]
        print(json.dumps(sample, indent=2))
