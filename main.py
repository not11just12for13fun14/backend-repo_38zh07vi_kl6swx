import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

from database import db, create_document, get_documents
from schemas import Device, Alert, SmartPerformance

app = FastAPI(title="UEM Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "UEM Dashboard Backend Running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
            except Exception as e:
                response["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# Seed demo data if collections are empty (idempotent)
@app.post("/seed", tags=["demo"])
def seed_demo_data():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # Only seed if empty
    if db["device"].count_documents({}) == 0:
        devices = [
            {"device_id": "D-1001", "hostname": "LAPTOP-01", "type": "laptop", "manufacturer": "Dell", "installed": True, "os": "Windows 11"},
            {"device_id": "D-1002", "hostname": "DESKTOP-01", "type": "desktop", "manufacturer": "HP", "installed": False, "os": "Windows 10"},
            {"device_id": "D-1003", "hostname": "LAPTOP-02", "type": "laptop", "manufacturer": "Lenovo", "installed": True, "os": "Windows 11"},
            {"device_id": "D-1004", "hostname": "DESKTOP-02", "type": "desktop", "manufacturer": "Dell", "installed": True, "os": "Windows 10"},
            {"device_id": "D-1005", "hostname": "LAPTOP-03", "type": "laptop", "manufacturer": "Acer", "installed": False, "os": "Windows 10"}
        ]
        db["device"].insert_many(devices)

    if db["alert"].count_documents({}) == 0:
        alerts = [
            {"device_id": "D-1001", "severity": "critical", "component": "CPU", "message": "CPU over 95% for 10m", "timestamp": datetime.utcnow()},
            {"device_id": "D-1002", "severity": "warning", "component": "HDD", "message": "Disk fragmented", "timestamp": datetime.utcnow()},
            {"device_id": "D-1003", "severity": "warning", "component": "RAM", "message": "High memory usage", "timestamp": datetime.utcnow()},
            {"device_id": "D-1004", "severity": "critical", "component": "Battery", "message": "Battery health low", "timestamp": datetime.utcnow()},
            {"device_id": "D-1005", "severity": "warning", "component": "CPU", "message": "Background process spike", "timestamp": datetime.utcnow()},
            {"device_id": "D-1001", "severity": "critical", "component": "HDD", "message": "SMART errors detected", "timestamp": datetime.utcnow()}
        ]
        db["alert"].insert_many(alerts)

    if db["smartperformance"].count_documents({}) == 0:
        perf = {
            "period": "week",
            "disk_reclaimed_count": 120,
            "tune_pc_fix_count": 85,
            "malware_fix_count": 32,
            "internet_performance_count": 74,
        }
        db["smartperformance"].insert_one(perf)

    return {"status": "ok"}

# Dashboard aggregated metrics endpoint
@app.get("/dashboard", tags=["dashboard"])
def get_dashboard():
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    # SmartPerformance (latest doc)
    sp = db["smartperformance"].find_one(sort=[("_id", -1)]) or {}

    # Device info aggregations
    total_devices = db["device"].count_documents({})
    installed_count = db["device"].count_documents({"installed": True})
    not_installed_count = db["device"].count_documents({"installed": False})
    laptop_count = db["device"].count_documents({"type": "laptop"})
    desktop_count = db["device"].count_documents({"type": "desktop"})

    # Manufacturer-wise counts
    pipeline = [{"$group": {"_id": "$manufacturer", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    manufacturer_counts = [
        {"manufacturer": d["_id"], "count": d["count"]}
        for d in db["device"].aggregate(pipeline)
    ]

    # Alerts section
    critical_count = db["alert"].count_documents({"severity": "critical"})
    warning_count = db["alert"].count_documents({"severity": "warning"})

    # Alerts by component
    comp_pipeline = [{"$group": {"_id": "$component", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
    alerts_by_component = [
        {"component": d["_id"], "count": d["count"]}
        for d in db["alert"].aggregate(comp_pipeline)
    ]

    # Top 5 alerts (most recent)
    top_alerts = list(db["alert"].find().sort("timestamp", -1).limit(5))
    for a in top_alerts:
        a["id"] = str(a.pop("_id", ""))

    return {
        "smart_performance": {
            "disk_reclaimed_count": sp.get("disk_reclaimed_count", 0),
            "tune_pc_fix_count": sp.get("tune_pc_fix_count", 0),
            "malware_fix_count": sp.get("malware_fix_count", 0),
            "internet_performance_count": sp.get("internet_performance_count", 0),
        },
        "device_info": {
            "total": total_devices,
            "installed": installed_count,
            "not_installed": not_installed_count,
            "laptops": laptop_count,
            "desktops": desktop_count,
            "manufacturers": manufacturer_counts,
        },
        "alerts": {
            "critical": critical_count,
            "warning": warning_count,
            "by_component": alerts_by_component,
            "top5": top_alerts,
        },
    }

# Expose schemas for viewer tools
@app.get("/schema")
def get_schema_definitions():
    return {
        "device": Device.model_json_schema(),
        "alert": Alert.model_json_schema(),
        "smartperformance": SmartPerformance.model_json_schema(),
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
