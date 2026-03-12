"""
Markets module config: supported feeds and constants.
"""

# Feed codes that have market integration (must match feeds.csv / app usage)
SUPPORTED_MARKET_FEEDS = ("bet365", "bwin", "1xbet", "betfair")

# Domain market CSV fields (align with main.py _ENTITY_FIELDS["markets"])
DOMAIN_MARKET_FIELDS = ("domain_id", "code", "name")
