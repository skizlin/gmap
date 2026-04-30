"""
API request/response models (Pydantic). Used by FastAPI routes in main.py.
"""
from pydantic import BaseModel
from typing import List, Optional, Union


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
    competition: Optional[str] = None  # competition display name (teams: infer country from parent category)
    country: Optional[str] = None  # ISO country code or '-' for categories/competitions/teams
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
    domain_id: str  # e.g. S-1, G-2, C-3, P-4
    name: str
    country: Optional[str] = None  # categories/competitions/teams only
    baseid: Optional[str] = None
    participant_type_id: Optional[int] = None
    underage_category_id: Optional[int] = None
    is_amateur: Optional[bool] = None


class UpdateEntityCountryRequest(BaseModel):
    entity_type: str  # "categories" | "competitions" | "teams"
    domain_id: str
    country: str


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
    active: Optional[bool] = None


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
    # Bwin/Bet365/1xbet use numeric ids; IMLog uses string template ids (e.g. IMLOG_CORRECT_SET_SCORE).
    id: Optional[Union[int, str]] = None
    name: Optional[str] = None
    feed_market_id: Optional[str] = None
    feed_market_name: Optional[str] = None


class SaveMarketTypeMappingsRequest(BaseModel):
    domain_market_id: str  # e.g. M-3
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
    sport_id: Optional[str] = None  # domain sport e.g. S-1


class UpdateMarginTemplateRequest(BaseModel):
    name: Optional[str] = None
    short_name: Optional[str] = None
    pm_margin: Optional[str] = None
    ip_margin: Optional[str] = None
    cashout: Optional[str] = None
    betbuilder: Optional[str] = None
    bet_delay: Optional[str] = None
    risk_class_id: Optional[int] = None


class AssignCompetitionToTemplateRequest(BaseModel):
    """Move a competition into a margin template (within current scope)."""
    template_id: int
    competition_id: str  # e.g. C-12
    brand_id: Optional[int] = None  # scope: None/empty = Global
    sport_id: Optional[str] = None  # domain sport id e.g. S-1


class CopyFromBrandRequest(BaseModel):
    """Copy all margin templates and their settings from one brand to another (same sport)."""
    source_brand_id: Optional[int] = None  # None = Global
    target_brand_id: Optional[int] = None  # None = Global
    sport_id: str  # domain sport id e.g. S-1


# ── RBAC ───────────────────────────────────────────────────────────────────

class CreateRbacUserRequest(BaseModel):
    email: str  # mandatory
    login: Optional[str] = None  # optional; default from email
    display_name: Optional[str] = None
    partner_id: Optional[int] = None
    active: Optional[bool] = True
    role_ids: Optional[List[int]] = None  # assign these roles on create
    brand_ids: Optional[List[int]] = None  # optional brand scope when partner-scoped
    is_superadmin: Optional[bool] = None  # developer bootstrap; API enforces who may set this
    login_pin: Optional[str] = None  # sign-in PIN for non–SuperAdmin users; default 1234 if omitted


class UpdateRbacUserRequest(BaseModel):
    email: Optional[str] = None
    login: Optional[str] = None
    display_name: Optional[str] = None
    partner_id: Optional[int] = None
    active: Optional[bool] = None
    role_ids: Optional[List[int]] = None
    brand_ids: Optional[List[int]] = None
    is_superadmin: Optional[bool] = None
    login_pin: Optional[str] = None  # non–SuperAdmin only; omit to leave unchanged


class AssignUserRolesRequest(BaseModel):
    role_ids: List[int]


class CreateRbacRoleRequest(BaseModel):
    name: str
    active: Optional[bool] = True
    partner_id: Optional[int] = None  # None/empty = Platform role
    permission_codes: Optional[List[str]] = None
    is_master: Optional[bool] = False  # exactly one master role per partner scope (including Platform)


class UpdateRbacRoleRequest(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None
    permission_codes: Optional[List[str]] = None
    is_master: Optional[bool] = None  # setting True clears master on other roles for same partner


class UpdateRolePermissionsRequest(BaseModel):
    """Full set of permission codes for a role (replaces existing)."""
    permission_codes: List[str]


