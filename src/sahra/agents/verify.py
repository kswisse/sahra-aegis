from ..coordinator import AgentBase
from ..protocol import AgentRole, Message, MessageKind
from ..types import ActionRecord


class VerifyAgent(AgentBase):
    """Holds the decided actions; invariants arrive in Task 5."""

    role = AgentRole.VERIFY
    emits = frozenset()

    def __init__(self) -> None:
        self.last_actions: list[ActionRecord] = []

    def handle(self, message: Message) -> list[Message]:
        self.last_actions = list(message.payload.actions)
        return []
