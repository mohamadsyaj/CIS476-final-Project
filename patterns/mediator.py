from typing import Dict, Any, Optional


class UIComponent:
    def __init__(self, name: str, mediator: Optional['UIMediator'] = None):
        self.name = name
        self.mediator = mediator

    def send(self, event: str, payload: Any = None):
        if self.mediator:
            self.mediator.notify(self, event, payload)

    def receive(self, event: str, payload: Any = None):
        # Components should override this method to handle messages
        pass


class UIMediator:
    """Simple mediator to coordinate UI components.

    This is a minimal implementation used by the app to decouple components
    — suitable for wiring frontend components or form handlers in the future.
    """

    def __init__(self):
        self._components: Dict[str, UIComponent] = {}

    def register(self, component: UIComponent) -> None:
        self._components[component.name] = component
        component.mediator = self

    def unregister(self, name: str) -> None:
        comp = self._components.pop(name, None)
        if comp:
            comp.mediator = None

    def notify(self, sender: UIComponent, event: str, payload: Any = None) -> None:
        # Broadcast to all components except sender
        for name, comp in self._components.items():
            if comp is sender:
                continue
            try:
                comp.receive(event, payload)
            except Exception:
                # swallow component errors to keep mediator robust
                pass
