"""Controls / validation recall on injected errors."""


def test_control_rules_fire(controls):
    rules = set(controls["rule_id"])
    for r in ["C1", "C2", "C4", "C5", "C6", "C7", "C8"]:
        assert r in rules, f"rule {r} did not fire"


def test_inventory_mismatch_detected(raw, controls):
    inj_ids = set(
        raw["inventory"][raw["inventory"]["injected_error"] == "inventory_mismatch"][
            "inventory_id"
        ].astype(str)
    )
    c5 = set(controls[controls["rule_id"] == "C5"]["entity_id"].astype(str))
    assert inj_ids, "no injected inventory mismatches"
    assert inj_ids.issubset(c5)


def test_wrong_vendor_detected(raw, controls):
    inj_ids = set(
        raw["bank_transactions"][
            raw["bank_transactions"]["injected_error"] == "wrong_vendor_mapping"
        ]["transaction_id"].astype(str)
    )
    c7 = set(controls[controls["rule_id"] == "C7"]["entity_id"].astype(str))
    assert inj_ids, "no injected wrong-vendor rows"
    assert inj_ids.issubset(c7)


def test_duplicate_bank_detected(raw, controls):
    inj_ids = set(
        raw["bank_transactions"][raw["bank_transactions"]["injected_error"] == "duplicate_bank"][
            "transaction_id"
        ].astype(str)
    )
    c8 = set(controls[controls["rule_id"] == "C8"]["entity_id"].astype(str))
    assert inj_ids, "no injected duplicate-bank rows"
    assert inj_ids.issubset(c8)


def test_timing_diff_detected(raw, controls):
    inj_ids = set(
        raw["payments"][raw["payments"]["injected_error"] == "timing_diff"]["payment_id"].astype(
            str
        )
    )
    c6 = set(controls[controls["rule_id"] == "C6"]["entity_id"].astype(str))
    assert inj_ids, "no injected timing rows"
    assert inj_ids.issubset(c6)


def test_unauthorized_payment_detected(raw, controls):
    inj_ids = set(
        raw["payments"][
            raw["payments"]["injected_error"] == "unauthorized_payment"
        ]["payment_id"].astype(str)
    )
    c2 = set(controls[controls["rule_id"] == "C2"]["entity_id"].astype(str))
    assert inj_ids, "no injected unauthorized payments"
    assert inj_ids.issubset(c2)
