from __future__ import annotations

from src.analysis.readside.editorial_summary_parts.cluster_summary import (
    build_cluster_editorial_summary,
)
from src.analysis.readside.editorial_summary_parts.comparative_metrics import (
    average_dimension_index,
    build_cluster_comparative_metrics,
    build_divergence_signals,
    compute_source_dimension_index,
    example_article_ids_for_dimension,
    is_editorial_row_usable_for_dimension,
    map_bias_direction,
    map_opinionatedness,
    map_tone,
)
from src.analysis.readside.editorial_summary_parts.json_payloads import (
    parse_json_list,
    parse_json_object,
    parse_json_scalar_list,
)
from src.analysis.readside.editorial_summary_parts.product_summary import (
    shape_member_editorial_preview,
    shape_product_editorial_summary,
)
from src.analysis.readside.editorial_summary_parts.review_flags import build_review_flags

__all__ = [
    "average_dimension_index",
    "build_cluster_comparative_metrics",
    "build_cluster_editorial_summary",
    "build_divergence_signals",
    "build_review_flags",
    "compute_source_dimension_index",
    "example_article_ids_for_dimension",
    "is_editorial_row_usable_for_dimension",
    "map_bias_direction",
    "map_opinionatedness",
    "map_tone",
    "parse_json_list",
    "parse_json_object",
    "parse_json_scalar_list",
    "shape_member_editorial_preview",
    "shape_product_editorial_summary",
]
