import asyncio
import json
import os
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

log = logging.getLogger("producer_ingest")
logging.basicConfig(level=logging.INFO)

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
                "meta": {"worker": "ingest-service"}
            }
            await producer.send_and_wait(TOPIC, json.dumps(loaded_evt).encode(), key=str(id_obj).encode())
            log.info("Ingest: published ObjectLoaded for %s", id_obj)
    finally:
        await consumer.stop()
        await producer.stop()
        log.info("ingest producer stopped")

if __name__ == "__main__":
    asyncio.run(run())
