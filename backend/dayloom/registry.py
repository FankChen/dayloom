import importlib
import inspect
import pkgutil


class Registry:
    def __init__(self):
        self.classes: dict[str, type] = {}

    def register(self, implementation: type):
        name = implementation.__name__
        if name in self.classes:
            raise ValueError(f"Duplicate plugin: {name}")
        self.classes[name] = implementation
        return implementation

    def discover(self, package_name: str):
        package = importlib.import_module(package_name)
        for module in pkgutil.iter_modules(package.__path__, f"{package_name}."):
            importlib.import_module(module.name)

    def build(self, name: str, **dependencies):
        implementation = self.classes[name]
        parameters = inspect.signature(implementation).parameters
        arguments = {key: dependencies[key] for key in parameters if key in dependencies}
        return implementation(**arguments)


tools = Registry()
providers = Registry()
connectors = Registry()


def discover_plugins():
    tools.discover("dayloom.tools")
    providers.discover("dayloom.providers")
    connectors.discover("dayloom.connectors")
