"""Tests for config module."""

import json
import os
from pathlib import Path

import pytest

from cascade.config import DEFAULT_CONFIG, load_config, save_config


class TestConfig:
    def test_default_config_structure(self):
        assert "provider" in DEFAULT_CONFIG
        assert "model" in DEFAULT_CONFIG
        assert "api_key" in DEFAULT_CONFIG

    def test_load_config_returns_dict(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cascade.config.CONFIG_FILE", tmp_path / "config.json")
        config = load_config()
        assert isinstance(config, dict)
        assert config["provider"] == DEFAULT_CONFIG["provider"]

    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr("cascade.config.CONFIG_FILE", tmp_path / "config.json")
        test_config = {"provider": "test", "model": "test-model", "api_key": "secret"}
        save_config(test_config)
        loaded = load_config()
        assert loaded["provider"] == "test"
        assert loaded["model"] == "test-model"
