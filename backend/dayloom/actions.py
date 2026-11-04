from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from dayloom.db import Action, as_dict, record
from dayloom.policy import action_digest
from dayloom.registry import tools
from dayloom.schemas import Proposal


def action_view(action):
    return {
        key: value
        for key, value in as_dict(action).items()
        if key not in {"approved_digest", "claim_token", "lease_until"}
    }


def get_action(session, action_id):
    action = session.scalar(select(Action).where(Action.id == action_id).with_for_update())
    if not action:
        raise HTTPException(404, "Action not found")
    return action


def validate_proposal(proposal: Proposal):
    implementation = tools.classes.get(proposal.tool)
    if implementation is None:
        raise HTTPException(422, "Unknown tool")
    try:
        return implementation.input_model.model_validate(proposal.payload).model_dump(mode="json")
    except ValidationError as error:
        raise HTTPException(422, "Invalid action payload") from error


def add_proposal(session, proposal: Proposal, agent_run_id=None):
    payload = validate_proposal(proposal)
    action = Action(
        tool=proposal.tool,
        payload=payload,
        digest=action_digest(proposal.tool, payload),
        agent_run_id=agent_run_id,
    )
    session.add(action)
    session.flush()
    record(session, "action.proposed", action.id, tool=action.tool)
    return action
