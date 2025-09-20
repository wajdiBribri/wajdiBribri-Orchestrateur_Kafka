from fastapi import FastAPI
from .orchestrator import Orchestrator
from .kafka_client import KafkaClient
import os
from aiokafka import AIOKafkaConsumer
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # ton frontend Angular
    allow_credentials=True,
    allow_methods=["*"],  # accepte POST, GET, OPTIONS...
    allow_headers=["*"],  # accepte tous les headers
)
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
OBJETS_PATH = os.getenv("OBJETS_PATH", "/app/Objets.json")

kclient = KafkaClient(bootstrap_servers=KAFKA_BOOTSTRAP)
orch = Orchestrator(objets_path=OBJETS_PATH, kafka_client=kclient)

@app.on_event("startup")
async def startup_event():
    await kclient.start()

@app.on_event("shutdown")
async def shutdown_event():
    await kclient.stop()

@app.post("/orchestrate")
async def orchestrate():
    order = await orch.run_once()
    return {"status": "ok", "count": len(order), "order_sample": order[:20]}

@app.get("/dag")
async def dag():
    orch.build_graph()
    sub = orch.extract_subgraph()
    return {"nodes": len(sub.nodes), "edges": len(sub.edges)}

@app.get("/events/last")
async def get_last_events(limit: int = 10):
    """
    Lit les derniers événements du topic Kafka `object.events`
    et retourne les N derniers en JSON.
    """
    consumer = AIOKafkaConsumer(
        "object.events",
        bootstrap_servers=KAFKA_BOOTSTRAP,
        group_id="orchestrator-debug",
        auto_offset_reset="latest",
        enable_auto_commit=False
    )

    await consumer.start()
    results = []
    try:
        # Poll une seule fois pour récupérer quelques messages récents
        msgs = await consumer.getmany(timeout_ms=1000, max_records=limit)
        for tp, batch in msgs.items():
            for msg in batch:
                try:
                    event = msg.value.decode()
                    results.append(event)
                except Exception:
                    results.append(str(msg.value))
    finally:
        await consumer.stop()

    return {"last_events": results}

@app.get("/events/stream")
async def stream_events():
    async def event_generator():
        consumer = AIOKafkaConsumer(
            "object.events",
            bootstrap_servers=KAFKA_BOOTSTRAP,
            group_id="orchestrator-stream",
            auto_offset_reset="latest",
            enable_auto_commit=True
        )
        await consumer.start()
        try:
            while True:
                msg = await consumer.getone()  # récupère un message à la fois
                try:
                    event = json.loads(msg.value.decode())
                except Exception:
                    event = {"raw": msg.value.decode(errors="ignore")}
                yield f"data: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            # Fin propre si le client se déconnecte
            pass
        finally:
            await consumer.stop()

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/dag/json")
async def dag_json():
    orch.build_graph()
    sub = orch.extract_subgraph()
    return orch.to_dict(sub)

@app.get("/dag/dot")
async def dag_dot():
    orch.build_graph()
    sub = orch.extract_subgraph()
    return StreamingResponse(
        iter([orch.to_dot(sub)]),
        media_type="text/plain"
    )
