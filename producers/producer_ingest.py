import asyncio
from datetime import datetime
import json
import os
import logging

import requests
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from prometheus_client import Counter, start_http_server

start_http_server(8002)  # port différent pour ce producer

EVENTS_PUBLISHED = Counter(
    "events_published_total",
    "Total events published by producer_ingest",
    ["status", "producer"]
)

log = logging.getLogger("producer_ingest")




logging.basicConfig(level=logging.INFO)

LOKI_URL = "http://loki:3100/loki/api/v1/push"  # adapte selon ton infra

def log_event_to_loki(event: dict, producer: str):
    """
    Envoie l'événement Kafka à Loki pour visualisation en timeline Grafana
    """
    ts = int(datetime.utcnow().timestamp() * 1e9)  # ns epoch pour Loki
    stream = {
        "stream": {
            "app": "kafka-orchestrator",
            "producer": producer,
            "event_type": event["event_type"],
        },
        "values": [
            [str(ts), json.dumps(event)]
        ],
    }
    payload = {"streams": [stream]}
    try:
        requests.post(LOKI_URL, json=payload, timeout=2)
    except Exception as e:
        print(f"[WARN] Failed to push event to Loki: {e}")


KAFKA = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = "object.events"

# tranche ingestion (début de chaine)
MIN_ID = 1000
MAX_ID = 1999

async def run():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA,
        group_id="ingest-service",
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA)
    await consumer.start()
    await producer.start()
    log.info("ingest producer started")
    try:
        async for msg in consumer:
            try:
                evt = json.loads(msg.value.decode())
            except Exception:
                log.warning("invalid json: %s", msg.value)
                continue

            if evt.get("event_type") != "ObjectReady":
                continue

            try:
                id_obj = int(evt.get("id_objet", -1))
            except Exception:
                continue

            # only handle ingestion range
            if not (MIN_ID <= id_obj <= MAX_ID):
                continue

            log.info("Ingest: handling id %s", id_obj)
            # simulate ingestion work
            await asyncio.sleep(0.5)

            loaded_evt = {
                "event_type": "ObjectLoaded",
                "id_objet": id_obj,
                "meta": {"worker": "ingest-service"},
                "event_datetime":datetime.now().isoformat()
            }
            await producer.send_and_wait(TOPIC, json.dumps(loaded_evt).encode(), key=str(id_obj).encode())
            EVENTS_PUBLISHED.labels(status="ObjectLoaded", producer="ingest").inc()
            log_event_to_loki(evt, producer="producer_ingest")
            log.info("Ingest: published ObjectLoaded for %s", id_obj)
    finally:
        await consumer.stop()
        await producer.stop()
        log.info("ingest producer stopped")

if __name__ == "__main__":
    asyncio.run(run())
