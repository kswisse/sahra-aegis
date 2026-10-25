from datetime import datetime

from ..coordinator import AgentBase
from ..fusion import fuse
from ..protocol import AgentRole, Message, MessageKind, ObservationPayload
from ..types import SatelliteReading, SiteReading, WeatherReading


class MonitorAgent(AgentBase):
    """Senses one zone: fuse the tiers into the state the cycle starts from."""

    role = AgentRole.MONITOR
    emits = frozenset({MessageKind.OBSERVATION})

    def handle(self, message: Message) -> list[Message]:
        return []

    def observe(
        self,
        zone_id: str,
        at: datetime,
        satellite: SatelliteReading | None,
        weather: WeatherReading,
        site: SiteReading | None,
        correlation_id: str,
    ) -> Message:
        state = fuse(zone_id, at, satellite, weather, site)
        return self.emit(
            MessageKind.OBSERVATION,
            AgentRole.PREDICT,
            ObservationPayload(state=state),
            correlation_id,
        )
