import pytest

from scripts.seed_catalog import _generate_catalog


def test_generate_catalog_success_accepts_maximum_total_chapter_count() -> None:
    """合計10件までのChapterを生成できることを確認する。"""
    catalog = _generate_catalog(2, 5)

    assert sum(len(textbook.chapters) for textbook in catalog) == 10


def test_generate_catalog_failure_rejects_total_chapter_count_over_limit() -> None:
    """合計10件を超えるChapterをDatabase投入前に拒否することを確認する。"""
    with pytest.raises(ValueError, match="total chapter count must be 10 or fewer"):
        _generate_catalog(1, 11)
