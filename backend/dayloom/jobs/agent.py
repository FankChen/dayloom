from dayloom.agents import advance_agent
from dayloom.registry import jobs


@jobs.register
class AgentLoop:
    def __init__(self, engine, settings, workspace_id):
        self.engine = engine
        self.settings = settings
        self.workspace_id = workspace_id

    def run_once(self):
        return advance_agent(self.engine, self.settings, self.workspace_id)
