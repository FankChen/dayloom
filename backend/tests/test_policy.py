import pytest
from dayloom.policy import action_digest, require_approval


def test_approval_is_bound_to_tool_and_payload():
    payload = {"title": "Prepare report", "minutes": 30}
    approval = action_digest("create_task", payload)
    require_approval("create_task", payload, approval)
    with pytest.raises(ValueError):
        require_approval("create_task", {**payload, "minutes": 60}, approval)
    with pytest.raises(ValueError):
        require_approval("save_memory", payload, approval)


def test_payload_order_does_not_change_approval():
    assert action_digest("create_task", {"title": "Report", "minutes": 30}) == action_digest(
        "create_task", {"minutes": 30, "title": "Report"}
    )


def test_missing_approval_is_rejected():
    with pytest.raises(ValueError):
        require_approval("create_task", {}, None)
