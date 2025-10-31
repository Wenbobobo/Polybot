from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, confloat, conint, conlist


class OutcomeSchema(BaseModel):
    id: str
    name: str


class MarketSchema(BaseModel):
    id: str
    title: str
    status: str
    outcomes: List[OutcomeSchema] = Field(default_factory=list)


Price = confloat(ge=0.0, le=1.0)
Size = confloat(ge=0.0)


class SnapshotMsg(BaseModel):
    type: Literal["snapshot"]
    seq: conint(ge=0)
    bids: List[conlist(float, min_length=2, max_length=2)] = Field(default_factory=list)
    asks: List[conlist(float, min_length=2, max_length=2)] = Field(default_factory=list)
    channel: Optional[str] = None
    market: Optional[str] = None
    ts_ms: Optional[conint(ge=0)] = None


class DeltaMsg(BaseModel):
    type: Literal["delta"]
    seq: conint(ge=0)
    bids: Optional[List[conlist(float, min_length=2, max_length=2)]] = None
    asks: Optional[List[conlist(float, min_length=2, max_length=2)]] = None
    checksum: Optional[str] = None
    channel: Optional[str] = None
    market: Optional[str] = None
    ts_ms: Optional[conint(ge=0)] = None
