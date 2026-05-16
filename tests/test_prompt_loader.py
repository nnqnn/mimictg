from pathlib import Path

import pytest

from app.services.ai.prompt_loader import PromptLoader


def test_prompt_loader_reads_prompt(tmp_path: Path):
    (tmp_path / "demo.md").write_text("Hello prompt", encoding="utf-8")

    loader = PromptLoader(tmp_path)

    assert loader.load("demo") == "Hello prompt"


def test_prompt_loader_fails_on_missing_prompt(tmp_path: Path):
    loader = PromptLoader(tmp_path)

    with pytest.raises(FileNotFoundError):
        loader.load("missing")

