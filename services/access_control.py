# =====================================================
# ACCESS CONTROL LAYER (PHASE 4 – P4-1)
# =====================================================

import streamlit as st
from config.subscription import DEFAULT_USER_TIER, get_tier_config


class AccessControl:
    """
    Centralized tier enforcement system.
    All feature gating MUST go through this layer.
    """

    def __init__(self):
        self.user_tier = st.session_state.get(
            "user_tier",
            DEFAULT_USER_TIER
        )
        self.tier_cfg = get_tier_config(self.user_tier)

    # -------------------------------------------------
    # CAPABILITY FLAGS
    # -------------------------------------------------
    
    @property
    def can_fast_refresh(self):
        return self.tier_cfg.get("fast_refresh", False)
    
    @property
    def scanner_limit(self):
        limit = self.tier_cfg.get("scanner_symbols", 1)
        if limit is None:  # ELITE unlimited
            return 9999
        return limit
    
    @property
    def can_live_options(self):
        # PRO and ELITE should have live options
        return self.user_tier in ["PRO", "ELITE"]
    
    @property
    def can_ml_advisory(self):
        return self.tier_cfg.get("show_ml_explanation", False)

    # -------------------------------------------------
    # HARD ENFORCEMENT METHODS
    # -------------------------------------------------

    def enforce_scanner_limit(self, requested_universe):
        """
        Enforces scanner universe cap.
        Returns trimmed list if necessary.
        """
        limit = self.scanner_limit

        if len(requested_universe) <= limit:
            return requested_universe

        return requested_universe[:limit]

    def enforce_feature(self, feature_flag: bool):
        """
        Hard guard for protected feature execution.
        """
        if not feature_flag:
            return False
        return True

    # -------------------------------------------------
    # VALIDATION
    # -------------------------------------------------

    def validate(self):
        """
        Defensive tier validation.
        Prevents invalid tiers from bypassing system.
        Also supports cloud-safe development override.
        """

        import os

        # -------------------------------------------------
        # CLOUD DETECTION (Auto-disable in production)
        # -------------------------------------------------
        IS_CLOUD = os.getenv("STREAMLIT_SERVER_HEADLESS") == "true"

        # -------------------------------------------------
        # SAFE DEV MODE OVERRIDE (Local Only)
        # -------------------------------------------------
        DEV_KEY = os.getenv("SMART_DASHBOARD_DEV_KEY")
        DEV_FORCE_TIER = os.getenv("DEV_FORCE_TIER")

        if (
            not IS_CLOUD
            and DEV_KEY == "ENABLE_TIER_OVERRIDE"
            and isinstance(DEV_FORCE_TIER, str)
        ):
            DEV_FORCE_TIER = DEV_FORCE_TIER.upper()

            from config.subscription import TIERS

            if DEV_FORCE_TIER in TIERS:
                self.user_tier = DEV_FORCE_TIER
                self.tier_cfg = get_tier_config(self.user_tier)
                return

        # -------------------------------------------------
        # NORMAL VALIDATION
        # -------------------------------------------------
        if not isinstance(self.user_tier, str):
            self.user_tier = DEFAULT_USER_TIER
            self.tier_cfg = get_tier_config(self.user_tier)