from __future__ import annotations

"""
Supabase client singleton with support for both JWT and new key formats.
"""

import re
from typing import Optional
from supabase import Client
import config

_client: Optional[Client] = None


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
    except Exception:
        pass


_patch_key_validation()


def get_client() -> Client:
    global _client
    if _client is None:
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
    return _client
