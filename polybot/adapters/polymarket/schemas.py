from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, confloat, conint


class OutcomeSchema(BaseModel):
    id: str
    name: str


class MarketSchema(BaseModel):
    id: str
    title: str
    status: str
    outcomes: List[OutcomeSchema] = Field(default_factory=list)


class SnapshotMsg(BaseModel):
    type: Literal["snapshot"]
    seq: conint(ge=0)
    bids: List[List[float]] = Field(default_factory=list)
    asks: List[List[float]] = Field(default_factory=list)
    channel: Optional[str] = None
    market: Optional[str] = None
    ts_ms: Optional[conint(ge=0)] = None


class DeltaMsg(BaseModel):
    type: Literal["delta"]
    seq: conint(ge=0)
    bids: Optional[List[List[float]]] = None
    asks: Optional[List[List[float]]] = None
    checksum: Optional[str] = None
    channel: Optional[str] = None
    market: Optional[str] = None
    ts_ms: Optional[conint(ge=0)] = None
