import importlib
import os
import sys

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def test_import_main(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "123456:TESTTOKEN")
    monkeypatch.setenv("CREDENTIALS_FILE", "creds.json")
    monkeypatch.setenv("ADMIN_IDS", "1")
    importlib.reload(importlib.import_module("main"))


def test_import_handlers():
    importlib.import_module("handlers")

