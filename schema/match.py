from typing import Optional
from typing import List
from .basemodel import Base
from .beatmap import BeatmapCompact
from .score import Score
from .user import User


class Game(Base):
    beatmap_id: int
    mods: List[str]
    beatmap: BeatmapCompact
    scores: List[Score]
    team_type: str


class Detail(Base):
    type: str


class Event(Base):
    id: int
    game: Optional[Game]
    detail: Detail
    timestamp: str


class Match(Base):
    match: dict
    events: List[Event]
    users: List[User]
