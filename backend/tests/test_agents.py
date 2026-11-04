import time

import pytest
from dayloom.agents import pause_run, planning_context
from dayloom.api import create_app
from dayloom.db import Action, AgentRun, AgentStep, Artifact, Integration, Workspace, identifier
from dayloom.registry import connectors, providers
from dayloom.schemas import AgentDecision, Proposal
from dayloom.worker import run_once
from dayloom.workspaces import WorkspaceSession
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session


def test_agent_records_persist_and_remain_workspace_scoped(engine):
    foreign_workspace = identifier()
    with Session(engine) as session:
        session.add(Workspace(id=foreign_workspace))
        session.commit()
    with WorkspaceSession(engine) as session:
        run = AgentRun(goal="Organize research", allowed_tools=["SaveArtifact"])
        session.add(run)
        session.flush()
        session.add(
            AgentStep(agent_run_id=run.id, ordinal=1, decision="ask_user", message="Which topic?")
        )
        session.add(
            Artifact(agent_run_id=run.id, title="Research", content="Verified local result")
        )
        session.commit()
        run_id = run.id
    with WorkspaceSession(engine) as session:
        assert session.get(AgentRun, run_id).status == "queued"
        assert session.scalar(select(AgentStep.message)) == "Which topic?"
        assert session.scalar(select(Artifact.content)) == "Verified local result"
    with WorkspaceSession(engine, workspace_id=foreign_workspace) as session:
        assert session.get(AgentRun, run_id) is None
        assert session.scalars(select(AgentStep)).all() == []
        assert session.scalars(select(Artifact)).all() == []


def test_v03_upgrade_preserves_tasks_and_approval_records(engine):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from dayloom.db import Task
    from dayloom.migrations import migrate
    from dayloom.policy import action_digest
    from sqlalchemy import inspect, text

    migrate(engine)
    payload = {"title": "Keep the approved work"}
    with Session(engine) as session:
        task = Task(title="Existing v0.3 task")
        action = Action(
            tool="CreateTask", payload=payload, digest=action_digest("CreateTask", payload)
        )
        session.add_all([task, action])
        session.commit()
        task_id, action_id = task.id, action.id
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        operations.drop_table("agent_steps")
        operations.drop_table("artifacts")
        convention = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
        with operations.batch_alter_table("actions", naming_convention=convention) as batch:
            batch.drop_index("ix_actions_agent_run_id")
            batch.drop_constraint("fk_actions_agent_run_id_agent_runs", type_="foreignkey")
            batch.drop_column("agent_run_id")
        operations.drop_table("agent_runs")
        connection.execute(text("UPDATE alembic_version SET version_num = '0005_automation'"))
    migrate(engine)
    migrate(engine)
    with Session(engine) as session:
        assert session.get(Task, task_id).title == "Existing v0.3 task"
        stored = session.get(Action, action_id)
        assert stored.payload == payload and stored.digest == action_digest("CreateTask", payload)
        assert stored.status == "pending" and stored.agent_run_id is None
        assert {"agent_runs", "agent_steps", "artifacts"}.issubset(
            inspect(engine).get_table_names()
        )
        assert (
            session.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0006_agents"
        )


def test_agent_decisions_require_exactly_one_action_or_a_final_message():
    with pytest.raises(ValidationError):
        AgentDecision(decision="act", message="Do something")
    with pytest.raises(ValidationError):
        AgentDecision(
            decision="finish",
            message="Done",
            proposal={"tool": "CreateTask", "payload": {"title": "Wrong"}},
        )
    assert AgentDecision(decision="ask_user", message="Which device?").proposal is None


def test_agent_context_excludes_unrelated_connection_metadata(engine, settings):
    with WorkspaceSession(engine) as session:
        session.add(
            Integration(
                kind="smtp",
                label="Private mailbox",
                configuration={"host": "smtp.gmail.com", "username": "private@example.com"},
                secret="not-read",
            )
        )
        run = AgentRun(goal="Search public sources", allowed_tools=["SearchWeb", "SaveArtifact"])
        session.add(run)
        session.commit()
        context = planning_context(session, run, settings)
        assert context["connections"] == []
        assert "private@example.com" not in str(context)


def test_explicit_offline_demo_produces_only_a_labeled_artifact(engine, settings):
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/agent/runs",
            json={"goal": "Test the approval flow", "allowed_tools": ["SaveArtifact"]},
        )
        assert response.status_code == 201
        run_id = response.json()["id"]
        assert run_once(engine, settings)
        assert client.get("/api/artifacts").json() == []
        action = client.get(f"/api/agent/runs/{run_id}").json()["steps_history"][-1]["action"]
        assert action["tool"] == "SaveArtifact"
        assert "Offline demonstration" in action["payload"]["content"]
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        assert run_once(engine, settings)
        assert run_once(engine, settings)
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "completed"
        assert client.get("/api/tasks").json() == []
        assert len(client.get("/api/artifacts").json()) == 1


def test_agent_replans_from_real_tool_results_and_finishes(engine, settings, monkeypatch):
    calls = []

    async def plan(self, goal, context):
        calls.append(context)
        completed = context["tool_results"]
        if not completed:
            return AgentDecision(
                decision="act",
                message="Create the requested task.",
                proposal=Proposal(tool="CreateTask", payload={"title": "Agent task"}),
            )
        if len(completed) == 1:
            assert completed[0]["status"] == "succeeded"
            assert completed[0]["result"] is not None
            return AgentDecision(
                decision="act",
                message="Remember the requested preference.",
                proposal=Proposal(
                    tool="SaveMemory", payload={"content": "I prefer morning research"}
                ),
            )
        assert all(result["status"] == "succeeded" for result in completed)
        return AgentDecision(
            decision="finish", message="Your requested task and preference were saved."
        )

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        response = client.post(
            "/api/agent/runs",
            json={
                "goal": "Create a task and remember my preference",
                "allowed_tools": ["CreateTask", "SaveMemory"],
                "max_steps": 3,
            },
        )
        assert response.status_code == 201
        run_id = response.json()["id"]
        assert client.get("/api/agent/tools").json()["model_ready"] is True
        assert "steps_history" not in client.get("/api/agent/runs").json()[0]
        assert calls == []
        for count in range(2):
            assert run_once(engine, settings)
            run = client.get(f"/api/agent/runs/{run_id}").json()
            assert run["status"] == "waiting_approval"
            action = run["steps_history"][-1]["action"]
            assert action["status"] == "pending"
            assert not run_once(engine, settings)
            assert (
                client.post(
                    f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
                ).status_code
                == 200
            )
            assert run_once(engine, settings)
            assert len(calls) == count + 1
        assert run_once(engine, settings)
        run = client.get(f"/api/agent/runs/{run_id}").json()
        assert run["status"] == "completed"
        assert run["steps"] == 3
        assert len(calls) == 3
        assert client.get("/api/tasks").json()[0]["title"] == "Agent task"
        assert client.get("/api/memories").json()[0]["content"] == "I prefer morning research"
        assert "claim_token" not in run and "lease_until" not in run
        assert client.get("/api/data").json()["agent_runs"][0]["id"] == run_id
        assert (
            client.delete("/api/data", headers={"X-Dayloom-Confirm": "DELETE MY DATA"}).status_code
            == 204
        )
        assert client.get("/api/agent/runs").json() == []


def test_agent_pause_revokes_pending_and_queued_actions(engine, settings, monkeypatch):
    async def plan(self, goal, context):
        return AgentDecision(
            decision="act",
            message="Create the task.",
            proposal=Proposal(tool="CreateTask", payload={"title": "Paused task"}),
        )

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        run_id = client.post(
            "/api/agent/runs", json={"goal": "Create task", "allowed_tools": ["CreateTask"]}
        ).json()["id"]
        assert run_once(engine, settings)
        action = client.get("/api/actions").json()[0]
        assert (
            client.post(
                f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
            ).status_code
            == 200
        )
        assert client.post(f"/api/agent/runs/{run_id}/pause").status_code == 200
        assert (
            client.post(
                f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]}
            ).status_code
            == 409
        )
        assert not run_once(engine, settings)
        assert client.get("/api/tasks").json() == []
        resumed = client.post(
            f"/api/agent/runs/{run_id}/resume",
            json={"message": "Please revise before proceeding", "max_steps": 8},
        )
        assert resumed.status_code == 200
        assert resumed.json()["steps_history"][-1]["decision"] == "user"
        assert client.get("/api/actions").json()[0]["status"] == "cancelled"


def test_agent_cancel_discards_a_late_model_decision(engine, settings, monkeypatch):
    with TestClient(create_app(settings)) as client:

        async def plan(self, goal, context):
            run_id = context["agent"]["run_id"]
            assert client.post(f"/api/agent/runs/{run_id}/cancel").status_code == 200
            return AgentDecision(
                decision="act",
                message="Too late",
                proposal=Proposal(tool="CreateTask", payload={"title": "Must not be created"}),
            )

        monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
        run_id = client.post(
            "/api/agent/runs", json={"goal": "Create task", "allowed_tools": ["CreateTask"]}
        ).json()["id"]
        assert run_once(engine, settings)
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "cancelled"
        assert client.get("/api/actions").json() == []


@pytest.mark.parametrize("reason", ["expired", "limit", "model", "interrupted"])
def test_agent_stops_before_extra_model_calls(engine, settings, monkeypatch, reason):
    async def forbidden(self, goal, context):
        raise AssertionError("No model request should be made")

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", forbidden, raising=False)
    with TestClient(create_app(settings)) as client:
        run_id = client.post(
            "/api/agent/runs", json={"goal": "Bounded goal", "allowed_tools": ["CreateTask"]}
        ).json()["id"]
        with Session(engine) as session:
            run = session.get(AgentRun, run_id)
            if reason == "expired":
                run.expires_at = time.time() - 1
            elif reason == "limit":
                run.steps = run.max_steps
            elif reason == "model":
                run.model_binding = {"name": "changed"}
            else:
                run.status = "planning"
                run.lease_until = time.time() - 1
            session.commit()
        assert run_once(engine, settings)
        run = client.get(f"/api/agent/runs/{run_id}").json()
        assert run["status"] == "paused"
        assert "planning failed" not in run["error"]
        assert client.get("/api/actions").json() == []


@pytest.mark.parametrize(
    "decision",
    [
        AgentDecision(decision="finish", message="Unsupported completion"),
        AgentDecision(
            decision="act",
            message="Not authorized",
            proposal=Proposal(tool="SaveMemory", payload={"content": "Not requested"}),
        ),
    ],
)
def test_agent_rejects_unsupported_completion_or_tool(engine, settings, monkeypatch, decision):
    async def plan(self, goal, context):
        return decision

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        run_id = client.post(
            "/api/agent/runs", json={"goal": "Create task", "allowed_tools": ["CreateTask"]}
        ).json()["id"]
        assert run_once(engine, settings)
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "paused"
        assert client.get("/api/actions").json() == []


def test_agent_needs_input_and_resume_preserves_scope(engine, settings, monkeypatch):
    contexts = []

    async def plan(self, goal, context):
        contexts.append(context)
        return AgentDecision(decision="ask_user", message="Which task title?")

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        run_id = client.post(
            "/api/agent/runs", json={"goal": "Create a task", "allowed_tools": ["CreateTask"]}
        ).json()["id"]
        assert run_once(engine, settings)
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "needs_input"
        assert (
            client.post(
                f"/api/agent/runs/{run_id}/resume",
                json={"message": "Research", "allowed_tools": ["SendEmail"]},
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/agent/runs/{run_id}/resume", json={"message": "Research"}
            ).status_code
            == 200
        )
        assert run_once(engine, settings)
        assert contexts[-1]["history"][-1] == {"decision": "user", "message": "Research"}


def test_agent_requires_explicit_model_sharing(settings, monkeypatch):
    async def plan(self, goal, context):
        raise AssertionError("No provider call expected")

    settings.model_provider = "OpenAIProvider"
    settings.model_api_key = SecretStr("synthetic-agent-test-key")
    monkeypatch.setattr(providers.classes["OpenAIProvider"], "plan", plan)
    with TestClient(create_app(settings)) as client:
        assert (
            client.post(
                "/api/agent/runs", json={"goal": "Private goal", "allowed_tools": ["CreateTask"]}
            ).status_code
            == 400
        )
        assert client.get("/api/agent/runs").json() == []


def test_agent_unknown_outcome_requires_reconciliation(engine, settings, monkeypatch):
    async def plan(self, goal, context):
        return AgentDecision(
            decision="act",
            message="Create task",
            proposal=Proposal(tool="CreateTask", payload={"title": "Pending outcome"}),
        )

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        run_id = client.post(
            "/api/agent/runs", json={"goal": "Create task", "allowed_tools": ["CreateTask"]}
        ).json()["id"]
        assert run_once(engine, settings)
        with Session(engine) as session:
            action = session.scalar(select(Action).where(Action.agent_run_id == run_id))
            action.status = "outcome_unknown"
            session.commit()
        assert run_once(engine, settings)
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "paused"
        assert client.post(f"/api/agent/runs/{run_id}/resume", json={}).status_code == 409


def test_agent_failure_handling_does_not_overwrite_a_concurrent_cancel(engine):
    with WorkspaceSession(engine) as session:
        run = AgentRun(goal="Cancelled goal", allowed_tools=["CreateTask"])
        session.add(run)
        session.commit()
        run_id = run.id
    with WorkspaceSession(engine) as stale_session:
        stale = stale_session.get(AgentRun, run_id)
        with WorkspaceSession(engine) as session:
            session.get(AgentRun, run_id).status = "cancelled"
            session.commit()
        pause_run(stale_session, stale, "Late failure")
    with WorkspaceSession(engine) as session:
        assert session.get(AgentRun, run_id).status == "cancelled"


def test_agent_api_does_not_expose_other_workspaces(engine, settings):
    with Session(engine) as session:
        workspace_id = identifier()
        session.add(Workspace(id=workspace_id))
        session.commit()
        run = AgentRun(workspace_id=workspace_id, goal="Private goal", allowed_tools=["CreateTask"])
        session.add(run)
        session.commit()
        run_id = run.id
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/agent/runs").json() == []
        assert client.get(f"/api/agent/runs/{run_id}").status_code == 404
        assert client.post(f"/api/agent/runs/{run_id}/pause").status_code == 404
        assert client.post(f"/api/agent/runs/{run_id}/cancel").status_code == 404
        assert client.post(f"/api/agent/runs/{run_id}/resume", json={}).status_code == 404


def test_agent_searches_then_saves_a_real_downloadable_artifact(engine, settings, monkeypatch):
    searches = []

    def search(self, query, max_results):
        searches.append(query)
        return [
            {
                "title": "Source",
                "href": "https://example.com/research",
                "body": "Public source evidence",
            },
            {"title": "Unsafe", "href": "javascript:alert(1)", "body": "Must be excluded"},
        ]

    async def plan(self, goal, context):
        results = context["tool_results"]
        if not results:
            return AgentDecision(
                decision="act",
                message="Search sources",
                proposal=Proposal(tool="SearchWeb", payload={"query": "research topic"}),
            )
        if len(results) == 1:
            assert results[0]["status"] == "succeeded"
            sources = results[0]["result"]["sources"]
            assert len(sources) == 1
            return AgentDecision(
                decision="act",
                message="Save findings",
                proposal=Proposal(
                    tool="SaveArtifact",
                    payload={
                        "title": "Research findings",
                        "content": "# Findings\nPublic source evidence",
                        "sources": [sources[0]["url"]],
                    },
                ),
            )
        assert results[-1]["result"]["kind"] == "artifact"
        return AgentDecision(decision="finish", message="The source-linked findings were saved.")

    monkeypatch.setattr(connectors.classes["PublicSearch"], "search", search)
    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        run_id = client.post(
            "/api/agent/runs",
            json={
                "goal": "Research and save findings",
                "allowed_tools": ["SearchWeb", "SaveArtifact"],
                "auto_readonly": True,
                "max_steps": 4,
            },
        ).json()["id"]
        assert run_once(engine, settings)
        assert run_once(engine, settings)
        assert searches == ["research topic"]
        assert run_once(engine, settings)
        run = client.get(f"/api/agent/runs/{run_id}").json()
        action = run["steps_history"][-1]["action"]
        assert action["tool"] == "SaveArtifact" and action["status"] == "pending"
        assert client.get("/api/artifacts").json() == []
        client.post(f"/api/actions/{action['id']}/approve", json={"digest": action["digest"]})
        assert run_once(engine, settings)
        assert run_once(engine, settings)
        assert client.get(f"/api/agent/runs/{run_id}").json()["status"] == "completed"
        artifact = client.get("/api/artifacts").json()[0]
        assert artifact["agent_run_id"] == run_id
        download = client.get(f"/api/artifacts/{artifact['id']}/download")
        assert download.status_code == 200
        assert download.text == "# Findings\nPublic source evidence"
        assert download.headers["content-disposition"].startswith("attachment;")
        assert client.get("/api/tasks").json() == []


def test_search_without_readonly_authorization_requires_approval(engine, settings, monkeypatch):
    async def plan(self, goal, context):
        return AgentDecision(
            decision="act",
            message="Search",
            proposal=Proposal(tool="SearchWeb", payload={"query": "query"}),
        )

    monkeypatch.setattr(providers.classes["DemoProvider"], "plan", plan, raising=False)
    with TestClient(create_app(settings)) as client:
        assert (
            client.post(
                "/api/agent/runs", json={"goal": "Search", "allowed_tools": ["SearchWeb"]}
            ).status_code
            == 201
        )
        assert run_once(engine, settings)
        assert client.get("/api/actions").json()[0]["status"] == "pending"
        assert not run_once(engine, settings)


def test_artifact_sources_are_validated_and_other_workspaces_cannot_read(engine, settings):
    from dayloom.tools.save_artifact import ArtifactInput

    with pytest.raises(ValidationError):
        ArtifactInput(title="Unsafe", content="Text", sources=["https://user:password@example.com"])
    with TestClient(create_app(settings)) as client:
        with Session(engine) as session:
            workspace_id = identifier()
            session.add(Workspace(id=workspace_id))
            session.commit()
            artifact = Artifact(workspace_id=workspace_id, title="Private", content="Not shared")
            session.add(artifact)
            session.commit()
            artifact_id = artifact.id
        assert client.get("/api/artifacts").json() == []
        assert client.get(f"/api/artifacts/{artifact_id}").status_code == 404
        assert client.get(f"/api/artifacts/{artifact_id}/download").status_code == 404
