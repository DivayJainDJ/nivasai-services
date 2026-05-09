"""Housing matcher package exports."""

from app.housing_matcher.service import HousingMatcherError, match_housing

__all__ = ["match_housing", "HousingMatcherError"]
