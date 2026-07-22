import pandas as pd
import pytest

from python_uk_bands.popularity_first_visuals import add_raw_reach_rank


def test_add_raw_reach_rank_preserves_rows_and_ranks_descending() -> None:
    strict = pd.DataFrame(
        {
            "study_city_label": ["Small", "Large", "Middle"],
            "band_count": [1, 5, 2],
            "monthly_listeners_total": [10, 50, 20],
            "rank_by_listener_reach_per_resident": [1, 3, 2],
        }
    )

    ranked = add_raw_reach_rank(strict)

    assert ranked["raw_reach_rank"].tolist() == [3, 1, 2]
    assert "raw_reach_rank" not in strict.columns
    assert len(ranked) == len(strict)


def test_add_raw_reach_rank_rejects_incomplete_input() -> None:
    with pytest.raises(ValueError, match="missing columns"):
        add_raw_reach_rank(
            pd.DataFrame(
                {
                    "study_city_label": ["Example"],
                    "monthly_listeners_total": [10],
                }
            )
        )
