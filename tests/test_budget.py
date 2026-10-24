import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "train"))
from budget import estimate_sft_usd, guard  # noqa: E402


def test_sft_estimate(): assert estimate_sft_usd(1_000_000, 1, "Qwen/Qwen3-8B") == pytest.approx(0.44)


def test_guard_aborts_over_cap():
    with pytest.raises(SystemExit):
        guard(2.0, 1.0)
