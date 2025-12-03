from typing import Dict, Any, Optional


class UIComponent:
    def __init__(self, name: str, mediator: Optional['UIMediator'] = None):
        self.name = name
        self.mediator = mediator  # The mediator this component talks through

    def send(self, event: str, payload: Any = None):
        # Tell the mediator that something happened
        if self.mediator:
            self.mediator.notify(self, event, payload)

    def receive(self, event: str, payload: Any = None):
        # Other components will override this
        pass


class UIMediator:
    def __init__(self):
        # Holds all registered UI components
        self._components: Dict[str, UIComponent] = {}

    def register(self, component: UIComponent) -> None:
        # Add component and connect it to this mediator
        self._components[component.name] = component
        component.mediator = self

    def unregister(self, name: str) -> None:
        # Remove component and disconnect it
        comp = self._components.pop(name, None)
        if comp:
            comp.mediator = None

    def notify(self, sender: UIComponent, event: str, payload: Any = None) -> None:
        # Send the event to every component except the sender
        for name, comp in self._components.items():
            if comp is sender:
                continue
            try:
                comp.receive(event, payload)
            except Exception:
                # Ignore errors from components
                pass
