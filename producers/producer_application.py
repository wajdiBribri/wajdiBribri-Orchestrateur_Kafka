import asyncio
from datetime import datetime
import json
import os
import logging

import requests
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from prometheus_client import Counter, start_http_server

start_http_server(8004)  # port différent pour ce producer
EVENTS_PUBLISHED = Counter(
    "events_published_total",
    "Total events published by producer_application",
    ["status", "producer"]
)

log = logging.getLogger("producer_application")
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

# tranche application (terminaux)
MIN_ID = 3000

async def process_event(producer, id_obj):
    """Process a single ObjectReady event and publish ObjectLoaded or ObjectFailed."""
    log.info("Application: handling id %s", id_obj)
    try:
        await asyncio.sleep(0.8)  # Simulate application-level work
        loaded_evt = {
            "event_type": "ObjectLoaded",
            "id_objet": id_obj,
            "meta": {"worker": "application-service"},
            "event_datetime":datetime.now().isoformat()
        }
        await producer.send_and_wait(TOPIC, json.dumps(loaded_evt).encode(), key=str(id_obj).encode())
        EVENTS_PUBLISHED.labels(status="ObjectLoaded", producer="application").inc()
        log_event_to_loki(loaded_evt, producer="producer_application")
        log.info("Application: published ObjectLoaded for %s", id_obj)
    except Exception as e:
        failed_evt = {
            "event_type": "ObjectFailed",
            "id_objet": id_obj,
            "meta": {"worker": "application-service", "error": str(e)},
            "event_datetime":datetime.now().isoformat()
        }
        await producer.send_and_wait(TOPIC, json.dumps(failed_evt).encode(), key=str(id_obj).encode())
        EVENTS_PUBLISHED.labels(status="ObjectFailed", producer="application").inc()
        log_event_to_loki(loaded_evt, producer="producer_application")
        log.exception("Application: failed processing %s", id_obj)

async def run():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA,
        group_id="application-service",
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA)
    await consumer.start()
    await producer.start()
    log.info("application producer started")
    try:
        # Collect events in a batch to process in parallel
        async def process_batch():
            tasks = []
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

                if id_obj < MIN_ID:
                    continue

                # Add event processing to tasks for parallel execution
                tasks.append(process_event(producer, id_obj))

                # Process tasks in parallel when batch is ready or loop yields
                if len(tasks) >= 2:  # Adjust batch size as needed
                    await asyncio.gather(*tasks)
                    tasks = []

            # Process any remaining tasks
            if tasks:
                await asyncio.gather(*tasks)

        await process_batch()
    finally:
        await consumer.stop()
        await producer.stop()
        log.info("application producer stopped")

if __name__ == "__main__":
    asyncio.run(run())