# MBTA Router

A project for Hack Club Macando. This is a Python script that plans the best way to get from one address to another in Boston using the MBTA subway and light rail (no buses or Silver Line yet).

Give it two addresses and it figures out: which station to walk to, what line(s) to ride, where to transfer, and the final walk to your destination. It tries to minimize walking and also tries to avoid boarding a train underground when there's a decent surface option (transferring or getting off underground is fine, since that doesn't cost anything extra either way -- it's specifically boarding that gets penalized).

## How it works

- Pulls all subway and light rail stations, plus their actual track connections, directly from the MBTA v3 API (using the `route_patterns` endpoint so stops come back in real travel order instead of guessed order).
- Converts addresses into GPS coordinates using a chain of geocoders, in order:
  1. **Nominatim** -- free, no API key required
  2. **LocationIQ** -- free tier, requires a key, better at resolving business names
  3. **Photon** -- free, no key required, used as a backup
  4. If none of the above can resolve the input, it falls back to asking **Gemini** to guess the actual address, then retries the geocoder chain with that.
- Builds a graph with `networkx` and runs Dijkstra's algorithm with a custom weight function that prioritizes riding the T over walking long distances.

## Setup

Create a `.env` file with the following:

```
MBTA_API_KEY=your key here (free from api-v3.mbta.com -- the script still works without one, just with lower rate limits)
LOCATIONIQ_API_KEY=optional, free signup at locationiq.com, no credit card required
GEMINI_API_KEY=optional, free from ai.google.dev, only used as a last-resort geocoding fallback
```

Install dependencies and run:

```
pip install streamlit networkx requests python-dotenv
python mbta_router.py
```

Edit the `origin` and `destination` variables at the bottom of the script to whatever locations you want.

## Known limitations

- Only covers subway and light rail -- no buses, Silver Line, or commuter rail.
- Gemini can occasionally hallucinate an address if it doesn't actually know the place, so if a route looks off, it's worth checking the resolved address before assuming the routing logic is at fault.
- Photon is a shared public instance and can return a 403 if it gets hit too often.
- Doesn't account for real train schedules or wait times -- it assumes you board immediately.

This started out fairly rough and got patched up as issues came up during testing, but it's in working shape now.
