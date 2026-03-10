from __future__ import annotations

"""
Supabase client singleton with support for both JWT and new key formats.
"""

import re
import logging
from typing import Optional
import config

logger = logging.getLogger(__name__)

_client = None


def _patch_key_validation():
    """Patch supabase-py to accept new sb_publishable_/sb_secret_ key formats."""
    try:
        from supabase._sync.client import SyncClient
        original_init = SyncClient.__init__

        def patched_init(self, supabase_url, supabase_key, options=None):
            if supabase_key and (
                supabase_key.startswith("sb_secret_")
                or supabase_key.startswith("sb_publishable_")
            ):
                _orig_match = re.match
                def _lenient_match(pattern, string, *args, **kwargs):
                    if pattern == r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$":
                        return True
                    return _orig_match(pattern, string, *args, **kwargs)

                old_re_match = re.match
                re.match = _lenient_match
                try:
                    original_init(self, supabase_url, supabase_key, options)
                finally:
                    re.match = old_re_match
            else:
                original_init(self, supabase_url, supabase_key, options)

        SyncClient.__init__ = patched_init
        logger.info("Supabase key validation patch applied.")
    except ImportError:
        logger.info("supabase._sync.client not found — skipping patch (may not be needed).")
    except Exception as e:
        logger.warning(f"Supabase patch failed (non-fatal): {e}")


_patch_key_validation()


def get_client():
    global _client
    if _client is None:
        from supabase import create_client
        url = config.SUPABASE_URL
        key = config.SUPABASE_SERVICE_KEY
        if not url or not key:
            raise RuntimeError(
                f"Missing Supabase config: SUPABASE_URL={'set' if url else 'MISSING'}, "
                f"SUPABASE_SERVICE_KEY={'set' if key else 'MISSING'}"
            )
        logger.info(f"Creating Supabase client for {url[:40]}...")
        _client = create_client(url, key)
        logger.info("Supabase client created.")
    return _client
