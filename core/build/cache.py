import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CACHE_DB = _REPO_ROOT / "memory" / "build_cache.db"
_CACHE_DB.parent.mkdir(parents=True, exist_ok=True)

class RemoteCacheProvider:
    """Abstraction for remote cache backends (S3, GCS, or Shared Filesystem)."""
    def __init__(self):
        self.backend = os.getenv("GEMFORGE_REMOTE_CACHE_BACKEND", "none") # s3, local_fs, none
        self.bucket = os.getenv("GEMFORGE_REMOTE_CACHE_BUCKET", "gemforge-cache")
        self.root_path = os.getenv("GEMFORGE_REMOTE_CACHE_PATH", str(_REPO_ROOT.parent / "gemforge-remote-cache"))
        
        if self.backend == "local_fs":
            Path(self.root_path).mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        if self.backend == "none":
            return None
            
        if self.backend == "local_fs":
            cache_file = Path(self.root_path) / f"{key}.json"
            if cache_file.exists():
                print(f"   🌐 [REMOTE CACHE] Hit for {key[:8]} (Local FS Backend)")
                return json.loads(cache_file.read_text())
        
        elif self.backend == "s3":
            try:
                import boto3
                s3 = boto3.client('s3')
                response = s3.get_object(Bucket=self.bucket, Key=f"cache/{key}.json")
                print(f"   🌐 [REMOTE CACHE] Hit for {key[:8]} (S3 Backend)")
                return json.loads(response['Body'].read().decode('utf-8'))
            except Exception:
                pass # Fail silently if remote is unreachable
        return None

    def set(self, key: str, value: Dict[str, Any]):
        if self.backend == "none":
            return
            
        if self.backend == "local_fs":
            cache_file = Path(self.root_path) / f"{key}.json"
            cache_file.write_text(json.dumps(value))
            
        elif self.backend == "s3":
            try:
                import boto3
                s3 = boto3.client('s3')
                s3.put_object(
                    Bucket=self.bucket, 
                    Key=f"cache/{key}.json", 
                    Body=json.dumps(value).encode('utf-8')
                )
            except Exception as e:
                print(f"   ⚠️ [REMOTE CACHE] Upload failed: {e}")

class BuildCache:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(_CACHE_DB)
        self.remote = RemoteCacheProvider()
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS build_cache (
                    input_hash TEXT NOT NULL,
                    step_id TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (input_hash, step_id)
                )
            """)
            conn.commit()

    def get(self, input_hash: str, step_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a cached result (check local first, then remote)."""
        # 1. Local Check
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT output_json FROM build_cache WHERE input_hash = ? AND step_id = ?",
                (input_hash, step_id)
            )
            row = cursor.fetchone()
            if row:
                print(f"   🎯 [CACHE] Local hit for {step_id} (hash: {input_hash[:8]})")
                return json.loads(row["output_json"])
        
        # 2. Remote Check
        remote_key = f"{step_id}_{input_hash}"
        remote_hit = self.remote.get(remote_key)
        if remote_hit:
            # Backfill local cache
            self.set(input_hash, step_id, remote_hit, skip_remote=True)
            return remote_hit
            
        return None

    def set(self, input_hash: str, step_id: str, output: Dict[str, Any], skip_remote: bool = False):
        """Store a result in the cache."""
        # 1. Local Store
        with sqlite3.connect(self.db_path, timeout=30) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO build_cache (input_hash, step_id, output_json, created_at) VALUES (?, ?, ?, ?)",
                (input_hash, step_id, json.dumps(output), datetime.now(timezone.utc).isoformat())
            )
            conn.commit()
            
        # 2. Remote Store (if enabled)
        if not skip_remote:
            remote_key = f"{step_id}_{input_hash}"
            self.remote.set(remote_key, output)

# Singleton
build_cache = BuildCache()
