from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.getenv("SUPABASE_URL") or ""
        key = os.getenv("SUPABASE_KEY") or ""
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in the environment")
        _supabase = create_client(url, key)
    return _supabase