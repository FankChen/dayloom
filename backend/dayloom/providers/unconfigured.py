from dayloom.registry import providers


@providers.register
class UnconfiguredProvider:
    external = True
    label = "Connect a model"

    async def reply(self, _content, _context):
        raise ValueError("A real model connection is required")
