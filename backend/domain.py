from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# --- Enums ---
class SportEnum(str, Enum):
    SOCCER = "Soccer"
    BASKETBALL = "Basketball"
    TENNIS = "Tennis"
    UNKNOWN = "Unknown"

class MappingStatus(str, Enum):
    UNMAPPED = "UNMAPPED"
    MAPPED = "MAPPED"
    IGNORED = "IGNORED"

# --- Domain Models (The "Golden Copy") ---

class UnifiedParticipant(BaseModel):
    """Represents a canonical team or player (e.g., 'Manchester United', ID: 1001)."""
    id: str = Field(..., description="Unique Domain ID (UUID or Hash)")
    name: str
    sport: SportEnum
    country: Optional[str] = None
    # External IDs mapping (Provider -> Native ID)
    external_ids: Dict[str, str] = Field(default_factory=dict) 

class UnifiedEvent(BaseModel):
    """Represents a unique, real-world match (e.g., 'Man Utd vs Liverpool')."""
    id: str = Field(..., description="Unique Domain ID")
    sport: SportEnum
    start_time: datetime
    
    # Participants
    home_participant: UnifiedParticipant
    away_participant: UnifiedParticipant
    
    # League/Tournament Info
    league_name: str
    season: str
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# --- Feed Models (Raw Data Containers) ---

class FeederEventDraft(BaseModel):
    """Raw event data coming from a feed provider (e.g., BetsAPI, bwin)."""
    feed_provider: str          # e.g., "bet365", "bwin"
    valid_id: str               # The native ID from the feed

    # Raw event participants
    raw_home_name: str
    raw_away_name: str
    raw_home_id: Optional[str] = None   # Team ID (absent in bwin)
    raw_away_id: Optional[str] = None   # Team ID (absent in bwin)

    # Raw competition hierarchy
    raw_league_name: Optional[str] = None
    raw_league_id: Optional[str] = None
    category: Optional[str] = None      # Country/Region (RegionName in bwin; parsed for others)
    category_id: Optional[str] = None   # RegionId in bwin; NULL for Unified API feeds

    # Timing
    start_time: datetime
    time_status: str = "0"              # "0" pre-match, "1" in-play, etc.

    # Sport
    sport: SportEnum

    # Cross-feed / bwin-specific fields
    betradar_id: Optional[int] = None   # BetRadarId from bwin; NULL for others
    is_outright: bool = False           # IsOutright from bwin; False for others
    market_name: Optional[str] = None   # Name of the specific market (e.g., 'Antepost Winner')
    is_mainbook: bool = False           # IsMainbook from bwin
    updated_at: Optional[int] = None    # Unix timestamp; bwin provides it; ingest time for others

    # Mapping state
    mapping_status: MappingStatus = MappingStatus.UNMAPPED
    domain_id: Optional[str] = None     # our_event_id / linked domain event ID
