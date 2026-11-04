"""Pure CPU adapter for WRD58 course-time auxiliary loss coefficients.

No model, torch, training launcher, tool execution or filesystem access. Call
before tensorization/padding using the reviewed loader's canonical features.
The caller applies one shared denominator to the whole accumulated step and
must disable any additional framework division by accumulation count.
"""
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import math

APPLIED_MARKER = "_wrd58_objective_already_applied"
PREPARED_SCHEMA = "wrd58-effective-objective-optimizer-step-v1"


def _require(value, message):
    if not value:
        raise ValueError(message)


def _exact(value):
    return Fraction(Decimal(str(value)))


def _scale(value):
    _require(isinstance(value, dict), "SCALE_MUST_BE_EXACT_FRACTION_OBJECT")
    result = Fraction(int(value["numerator"]), int(value["denominator"]))
    _require(result > 0 and result <= 1, "SCALE_OUTSIDE_ZERO_ONE")
    _require(math.isclose(float(result), value["float64"], rel_tol=1e-14, abs_tol=1e-15), "SCALE_FLOAT_AND_FRACTION_DISAGREE")
    return result


def _token_sha(tokens):
    h = hashlib.sha256()
    for token in tokens:
        h.update(int(token).to_bytes(4, "little"))
    return h.hexdigest()


def prepare_optimizer_step(step, loaded_rows):
    """Return new effective weights and the shared shifted-target denominator.

    ``step`` is one exact COURSE58 phase.steps entry. ``loaded_rows`` is a
    sequence in that step's microbatch order, each containing id, pool and
    the canonical four-feature ``features`` mapping from iter_features.

    Original input_ids/labels/attention_mask/loss_weights are never changed.
    Only the returned loss_weights are newly allocated. Returned features
    carry a marker and cannot be passed through this adapter a second time.
    An already-scaled array with a removed marker is rejected when its base
    weighted mass differs from the course's pinned unscaled mass.
    """
    _require(not isinstance(loaded_rows, dict), "ORDERED_LOADED_ROWS_REQUIRED")
    declared = step["microbatches"]
    _require(len(loaded_rows) == len(declared) > 0, "MICROBATCH_CARDINALITY_MISMATCH")
    _require(len({r["id"] for r in loaded_rows}) == len(loaded_rows), "REPEATED_TARGET_IN_STEP")
    alpha = _scale(step["auxiliary_extra_loss_scale"])
    denominator = 0
    real_mass = Fraction(0)
    aux_mass = Fraction(0)
    prepared = []
    for declared_row, loaded in zip(declared, loaded_rows):
        _require(loaded["id"] == declared_row["id"] and loaded["pool"] == declared_row["pool"], "COURSE_ID_POOL_OR_ORDER_MISMATCH")
        features = loaded["features"]
        _require(not features.get(APPLIED_MARKER), "REPEATED_OBJECTIVE_SCALING_REJECTED")
        ids = features["input_ids"]
        labels = features["labels"]
        weights = features["loss_weights"]
        attention = features["attention_mask"]
        _require(len(ids) == len(labels) == len(weights) == len(attention) > 1, "FOUR_FEATURE_LENGTH_MISMATCH")
        _require(labels[0] == -100 and weights[0] == 0, "UNSHIFTABLE_POSITION_ZERO_TARGET")
        positions = []
        mass = Fraction(0)
        for i, (token, label, weight, mask) in enumerate(zip(ids, labels, weights, attention)):
            _require(mask in (0, 1) and isinstance(token, int) and token >= 0, "INVALID_TOKEN_OR_ATTENTION")
            _require(math.isfinite(weight) and weight >= 0, "INVALID_BASE_WEIGHT")
            if label == -100:
                _require(weight == 0, "IGNORED_TARGET_HAS_NONZERO_WEIGHT")
            else:
                _require(i > 0 and mask == 1 and label == token and weight > 0, "INVALID_SHIFTED_POSITIVE_TARGET")
                positions.append(i)
                mass += _exact(weight)
        _require(positions, "EMPTY_SUPERVISION_MICROBATCH")
        _require(len(positions) == declared_row["positive_tokens"] == declared_row["valid_shifted_target_count"], "COURSE_TARGET_DENOMINATOR_DIFFERS")
        _require(_token_sha(labels[i] for i in positions) == declared_row["positive_token_ids_sha256_u32le"], "COURSE_POSITIVE_TOKEN_PAYLOAD_DIFFERS")
        _require(mass == _exact(declared_row["weighted_mass"]), "UNSCALED_BASE_MASS_MISMATCH_OR_REPEATED_SCALING")
        scale = _scale(declared_row["extra_course_loss_scale"])
        _require(scale == (alpha if loaded["pool"] == "synthetic" else 1), "WRONG_POOL_EXTRA_COURSE_SCALE")
        if loaded["pool"] == "synthetic":
            aux_mass += mass
        else:
            real_mass += mass
        effective = [float(_exact(w) * scale) if w else 0.0 for w in weights]
        effective_features = {
            "input_ids": ids,
            "labels": labels,
            "attention_mask": attention,
            "loss_weights": effective,
            APPLIED_MARKER: True,
        }
        prepared.append({"id": loaded["id"], "pool": loaded["pool"], "features": effective_features,
                         "extra_course_loss_scale": dict(declared_row["extra_course_loss_scale"]),
                         "base_positive_target_count": len(positions)})
        denominator += len(positions)
    _require(real_mass == _exact(step["original_real_weighted_mass"]) and aux_mass == _exact(step["original_auxiliary_weighted_mass"]), "COURSE_STEP_BASE_MASS_DIFFERS")
    _require(real_mass > 0 and aux_mass * alpha <= real_mass / 4, "AUXILIARY_EFFECTIVE_COEFFICIENT_MASS_CAP")
    _require((alpha == 1 and aux_mass <= real_mass / 4) or
             (alpha < 1 and aux_mass * alpha == real_mass / 4), "ALPHA_NOT_DECLARED_MAXIMAL_ALLOWED_SCALE")
    _require(denominator == step["valid_shifted_target_denominator"], "SHARED_DENOMINATOR_DIFFERS_FROM_COURSE")
    signature = hashlib.sha256(json.dumps(step, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {"schema": PREPARED_SCHEMA, "global_step_one_based": step["global_step_one_based"],
            "course_step_sha256": signature, "denominator": denominator,
            "microbatches": prepared, "base_features_mutated": False,
            "extra_accumulation_divisor": 1, "weights_sum_normalization": False,
            "coefficient_mass_cap_not_CE_gradient_or_Adam": True}


def reference_step_loss(prepared, token_losses_by_id):
    """Sum effective weight*CE over all microbatches, divide once by N_step.

    Each loss vector is aligned to target positions in labels and has the
    same length as labels. Position 0 and ignored targets contribute zero.
    This pure CPU reference does not compute model logits or backpropagate.
    """
    _require(prepared.get("schema") == PREPARED_SCHEMA, "PREPARED_OBJECTIVE_REQUIRED")
    _require(prepared["denominator"] > 0, "POSITIVE_SHARED_DENOMINATOR_REQUIRED")
    expected = {r["id"] for r in prepared["microbatches"]}
    _require(set(token_losses_by_id) == expected, "LOSS_VECTOR_IDS_DIFFER_FROM_STEP")
    parts = []
    for row in prepared["microbatches"]:
        f = row["features"]
        _require(f.get(APPLIED_MARKER) is True, "PREPARED_EFFECTIVE_WEIGHTS_REQUIRED")
        values = token_losses_by_id[row["id"]]
        _require(len(values) == len(f["labels"]), "TARGET_ALIGNED_LOSS_VECTOR_LENGTH")
        terms = []
        for i, (label, weight) in enumerate(zip(f["labels"], f["loss_weights"])):
            if i and label != -100:
                ce = values[i]
                _require(math.isfinite(ce) and ce >= 0, "INVALID_TOKEN_CE_VALUE")
                terms.append(weight * ce)
        parts.append(math.fsum(terms))
    return math.fsum(parts) / prepared["denominator"]
