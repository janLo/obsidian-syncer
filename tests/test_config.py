import os
import pytest
import tempfile
from obsidian_syncer.config import load_config, expand_env_vars, AppConfig

def test_expand_env_vars():
    os.environ["TEST_VAR"] = "test_value"
    assert expand_env_vars("value is ${TEST_VAR}") == "value is test_value"
    assert expand_env_vars("value is $TEST_VAR") == "value is test_value"
    
def test_load_config():
    yaml_content = """
    sync_sets:
      - name: test_set
        local_dir: /tmp/vault
        obsidian:
          enabled: true
        keep:
          enabled: false
          username: testuser
          password: testpassword
          tags: ["test"]
          target_folder: /tmp/vault/Keep
    """
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        f.write(yaml_content)
        temp_path = f.name
        
    try:
        config = load_config(temp_path)
        assert isinstance(config, AppConfig)
        assert len(config.sync_sets) == 1
        assert config.sync_sets[0].name == "test_set"
        assert config.sync_sets[0].obsidian is not None
        assert config.sync_sets[0].obsidian.enabled is True
        assert config.sync_sets[0].nextcloud is None
        assert config.sync_sets[0].keep is not None
        assert config.sync_sets[0].keep.enabled is False
    finally:
        os.remove(temp_path)
