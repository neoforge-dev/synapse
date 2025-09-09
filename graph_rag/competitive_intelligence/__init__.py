"""Competitive Intelligence Module for Epic 17 - Phase 2.

This module provides real-time competitive analysis and market positioning:
- Automated competitor analysis and tracking
- Market positioning engine with strategic insights
- Differentiation advisor for competitive advantages
- Strategic response recommendation system
"""

from .competitor_analyzer import CompetitorAnalyzer
from .market_positioning import MarketPositioningEngine
from .differentiation_advisor import DifferentiationAdvisor

__all__ = [
    "CompetitorAnalyzer",
    "MarketPositioningEngine", 
    "DifferentiationAdvisor"
]