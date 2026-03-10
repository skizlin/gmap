"""
API request/response models (Pydantic). Used by FastAPI routes in main.py.
"""
from pydantic import BaseModel
from typing import List, Optional


class CreateDomainEventRequest(BaseModel):
    feeder_provider: str
    feeder_valid_id: str
    sport: str
    category: Optional[str] = None
    competition: Optional[str] = None
    home: Optional[str] = None
    home_id: Optional[str] = None
    away: Optional[str] = None
    away_id: Optional[str] = None
    start_time: Optional[str] = None


class CreateEntityRequest(BaseModel):
    name: str
    entity_type: str  # "sports" | "categories" | "competitions" | "teams" | "markets"
    code: Optional[str] = None
    feed_id: Optional[str] = None
    feed_provider_id: Optional[int] = None
    feed_sport: Optional[str] = None
    feed_sport_id: Optional[str] = None
    sport: Optional[str] = None
    category: Optional[str] = None
    jurisdiction: Optional[str] = None
    baseid: Optional[str] = None
    participant_type_id: Optional[int] = None
    underage_category_id: Optional[int] = None
    is_amateur: Optional[bool] = None
    abb: Optional[str] = None
    market_type: Optional[str] = None
    market_group: Optional[str] = None
    template: Optional[str] = None
    period_type: Optional[str] = None
    score_type: Optional[str] = None
    side_type: Optional[str] = None
    score_dependant: Optional[bool] = None


class UpdateEntityNameRequest(BaseModel):
    entity_type: str  # "sports" | "categories" | "competitions" | "teams"
    domain_id: int
    name: str
    jurisdiction: Optional[str] = None
    baseid: Optional[str] = None
    participant_type_id: Optional[int] = None
    underage_category_id: Optional[int] = None
    is_amateur: Optional[bool] = None


class UpdateEntityJurisdictionRequest(BaseModel):
    entity_type: str  # "categories" | "competitions" | "teams"
    domain_id: int
    jurisdiction: str


class UpdateMarketRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    abb: Optional[str] = None
    market_type: Optional[str] = None
    market_group: Optional[str] = None
    template: Optional[str] = None
    period_type: Optional[str] = None
    score_type: Optional[str] = None
    side_type: Optional[str] = None
    score_dependant: Optional[bool] = None


class CreatePartnerRequest(BaseModel):
    name: str
    code: Optional[str] = None
    active: Optional[bool] = True


class UpdatePartnerRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    active: Optional[bool] = None


class CreateBrandRequest(BaseModel):
    name: str
    code: Optional[str] = None
    partner_id: Optional[int] = None
    jurisdiction: Optional[List[str]] = None
    language_ids: Optional[List[int]] = None
    currencies: Optional[List[str]] = None
    odds_formats: Optional[List[str]] = None


class UpdateBrandRequest(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    partner_id: Optional[int] = None
    jurisdiction: Optional[List[str]] = None
    language_ids: Optional[List[int]] = None
    currencies: Optional[List[str]] = None
    odds_formats: Optional[List[str]] = None


class CreateMarketGroupRequest(BaseModel):
    name: str
    code: Optional[str] = None


class MarketTypeMappingItem(BaseModel):
    feed_provider_id: int
    id: Optional[int] = None
    name: Optional[str] = None
    feed_market_id: Optional[str] = None
    feed_market_name: Optional[str] = None


class SaveMarketTypeMappingsRequest(BaseModel):
    domain_market_id: int
    prematch: List[MarketTypeMappingItem] = []
    live: List[MarketTypeMappingItem] = []


class CountryUpsertRequest(BaseModel):
    name: str
    cc: str
    original_cc: Optional[str] = None


class LanguageUpsertRequest(BaseModel):
    id: Optional[int] = None
    name: str
    native_name: Optional[str] = None
    direction: str = "ltr"
    active: bool = True


class TranslationUpsertRequest(BaseModel):
    entity_type: str
    entity_id: str
    field: str = "name"
    language_id: int
    text: str
    brand_id: Optional[int] = None


class CreateMarginTemplateRequest(BaseModel):
    name: str
    short_name: Optional[str] = None
    pm_margin: Optional[str] = None
    ip_margin: Optional[str] = None
    cashout: Optional[str] = None
    betbuilder: Optional[str] = None
    bet_delay: Optional[str] = None
    brand_id: Optional[int] = None  # None/empty = Global
    sport_id: Optional[int] = None


class UpdateMarginTemplateRequest(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    pm_margin: Optional[str] = None
    ip_margin: Optional[str] = None
    cashout: Optional[str] = None
    betbuilder: Optional[str] = None
    bet_delay: Optional[str] = None
    risk_class_id: Optional[int] = None


# ── RBAC ───────────────────────────────────────────────────────────────────

class CreateRbacUserRequest(BaseModel):
    email: str  # mandatory
    login: Optional[str] = None  # optional; default from email
    display_name: Optional[str] = None
    partner_id: Optional[int] = None
    active: Optional[bool] = True
    role_ids: Optional[List[int]] = None  # assign these roles on create
    brand_ids: Optional[List[int]] = None  # optional brand scope when partner-scoped


class UpdateRbacUserRequest(BaseModel):
    email: Optional[str] = None
    login: Optional[str] = None
    display_name: Optional[str] = None
    partner_id: Optional[int] = None
    active: Optional[bool] = None
    role_ids: Optional[List[int]] = None
    brand_ids: Optional[List[int]] = None


class AssignUserRolesRequest(BaseModel):
    role_ids: List[int]


class CreateRbacRoleRequest(BaseModel):
    name: str
    active: Optional[bool] = True
    partner_id: Optional[int] = None  # None/empty = Platform role
    permission_codes: Optional[List[str]] = None


class UpdateRbacRoleRequest(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    permission_codes: Optional[List[str]] = None


