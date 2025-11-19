"""
Database Schemas for UEM Dashboard

Each Pydantic model represents a MongoDB collection (collection name = lowercase class name).
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class Device(BaseModel):
    device_id: str = Field(..., description="Unique device identifier")
    hostname: str = Field(..., description="Device hostname")
    type: Literal["laptop", "desktop"] = Field(..., description="Form factor")
    manufacturer: str = Field(..., description="Manufacturer name")
    installed: bool = Field(..., description="Whether UEM agent is installed")
    os: Optional[str] = Field(None, description="Operating system")

class Alert(BaseModel):
    device_id: str = Field(..., description="Related device id")
    severity: Literal["critical", "warning", "info"] = Field(...)
    component: Literal["CPU", "HDD", "RAM", "Battery"] = Field(...)
    message: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SmartPerformance(BaseModel):
    period: str = Field(..., description="Aggregation period label, e.g., 'today', 'week', 'month'")
    disk_reclaimed_count: int = Field(0, ge=0)
    tune_pc_fix_count: int = Field(0, ge=0)
    malware_fix_count: int = Field(0, ge=0)
    internet_performance_count: int = Field(0, ge=0)
