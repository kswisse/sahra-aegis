from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Mapping, Sequence

from .protocol import AgentRole, Message, MessageKind, ProtocolViolation


class AgentBase(ABC):
    role: AgentRole
    emits: frozenset[MessageKind]
    coordinator: AgentCoordinator | None = None

    def bind(self, coordinator: AgentCoordinator) -> None:
        self.coordinator = coordinator

    @abstractmethod
    def handle(self, message: Message) -> list[Message]:
        ...

    def emit(
        self,
        kind: MessageKind,
        recipient: AgentRole,
        payload: object,
        correlation_id: str,
    ) -> Message:
        if kind not in self.emits:
            raise ProtocolViolation(
                f"{self.role.value} may not emit {kind.value}")
        return Message(
            correlation_id=correlation_id,
            sender=self.role,
            recipient=recipient,
            kind=kind,
            payload=payload,
        )


class AgentCoordinator:
    def __init__(self, agents: Mapping[AgentRole, AgentBase]) -> None:
        self._agents = dict(agents)
        for agent in self._agents.values():
            agent.bind(self)
        self._transcript: list[Message] = []

    @property
    def transcript(self) -> tuple[Message, ...]:
        return tuple(self._transcript)

    def run(self, seed: Sequence[Message]) -> tuple[Message, ...]:
        self._transcript.clear()
        queue = deque(seed)
        while queue:
            message = queue.popleft()
            sender = self._agents.get(message.sender)
            if sender is None:
                raise ProtocolViolation(
                    f"unregistered sender {message.sender.value}")
            if message.kind not in sender.emits:
                raise ProtocolViolation(
                    f"{message.sender.value} may not emit {message.kind.value}")
            recipient = self._agents.get(message.recipient)
            if recipient is None:
                raise ProtocolViolation(
                    f"unregistered recipient {message.recipient.value}")
            self._transcript.append(message)
            queue.extend(recipient.handle(message))
        return self.transcript
