"""Resolve sport code -> pricing model (volleyball first; extend as sports are added)."""


def get_model(sport_code: str):
    """Return the pricing model for sport_code, or None if not implemented."""
    code = (sport_code or "").strip().lower()
    if code == "volleyball":
        from .sports.volleyball.model import VolleyballPricingModel

        return VolleyballPricingModel()
    return None
