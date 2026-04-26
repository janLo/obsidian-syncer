import os
from typing import Optional
import yaml
from pydantic import BaseModel

class ObsidianConfig(BaseModel):
    enabled: bool = True

class NextcloudConfig(BaseModel):
    enabled: bool = True
    url: str
    user: str
    password: str
    remote_folder: str

class KeepConfig(BaseModel):
    enabled: bool = True
    username: str
    password: str
    tags: list[str]
    target_folder: str

class SyncSet(BaseModel):
    name: str
    local_dir: str
    obsidian: Optional[ObsidianConfig] = None
    nextcloud: Optional[NextcloudConfig] = None
    keep: Optional[KeepConfig] = None

class AppConfig(BaseModel):
    sync_sets: list[SyncSet]

def expand_env_vars(data: str) -> str:
    """Expands ${ENV_VAR} or $ENV_VAR in the given string."""
    return os.path.expandvars(data)

def load_config(file_path: str) -> AppConfig:
    with open(file_path, "r") as f:
        content = f.read()
    
    expanded_content = expand_env_vars(content)
    data = yaml.safe_load(expanded_content)
    return AppConfig(**data)
