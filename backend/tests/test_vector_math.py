import math
import pytest
from backend.vector_math import (
    DualIndex,
    LocalIndexFlatIP,
    angular_degrees,
    cosine_distance,
    cosine_similarity,
    dot_product,
    l2_norm,
    normalize,
)


def test_vector_math_dot_product_orthogonal():
    assert dot_product([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_vector_math_dot_product_parallel():
    assert dot_product([2.0, 3.0], [4.0, 5.0]) == 23.0


def test_vector_math_dot_product_length_mismatch_raises():
    with pytest.raises(ValueError, match="mismatch"):
        dot_product([1.0, 2.0], [1.0, 2.0, 3.0])


def test_vector_math_nan_inf_raises():
    with pytest.raises(ValueError, match="NaN or Inf"):
        dot_product([float("nan"), 1.0], [1.0, 2.0])
    with pytest.raises(ValueError, match="NaN or Inf"):
        l2_norm([float("inf"), 1.0])


def test_vector_math_l2_norm_calculation():
    assert l2_norm([3.0, 4.0]) == 5.0


def test_vector_math_normalize_zero_norm_returns_zeros():
    normed = normalize([0.0, 0.0, 0.0])
    assert normed == [0.0, 0.0, 0.0]


def test_vector_math_cosine_similarity_identical_and_opposite():
    v1 = [1.0, 2.0, 3.0]
    v2 = [-1.0, -2.0, -3.0]
    assert math.isclose(cosine_similarity(v1, v1), 1.0, rel_tol=1e-5)
    assert math.isclose(cosine_similarity(v1, v2), -1.0, rel_tol=1e-5)


def test_vector_math_cosine_similarity_zero_vector_never_nan():
    sim = cosine_similarity([0.0, 0.0], [1.0, 2.0])
    assert sim == 0.0
    assert not math.isnan(sim)


def test_vector_math_cosine_distance_relationship():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert math.isclose(cosine_distance(v1, v2), 1.0, rel_tol=1e-5)


def test_vector_math_angular_degrees_orthogonal():
    deg = angular_degrees([1.0, 0.0], [0.0, 1.0])
    assert math.isclose(deg, 90.0, rel_tol=1e-5)


def test_vector_math_local_index_flat_ip():
    idx = LocalIndexFlatIP(dim=3)
    idx.add(["c1", "c2"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    res = idx.search([1.0, 0.0, 0.0], top_k=2)
    assert len(res) == 2
    assert res[0][0] == "c1"
    assert math.isclose(res[0][1], 1.0, rel_tol=1e-5)


def test_vector_math_dual_index_cloud_query_blocked_in_airgap_mode():
    dual = DualIndex(airgap_dim=3, cloud_dim=3)
    dual.add_cloud(["c1"], [[1.0, 0.0, 0.0]], [{"meta": "1"}])
    with pytest.raises(ValueError, match="Never query a cloud index while mode == 'airgap'"):
        dual.search_cloud([1.0, 0.0, 0.0], top_k=1, mode="airgap")
