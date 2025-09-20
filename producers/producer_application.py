import asyncio
import json
import os
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

log = logging.getLogger("producer_application")
logging.basicConfig(level=logging.INFO)

KAFKA = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = "object.events"

# tranche application (terminaux)
MIN_ID = 3000

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

            log.info("Application: handling id %s", id_obj)
            # simulate application-level work
            try:
                await asyncio.sleep(0.8)
                loaded_evt = {
                    "event_type": "ObjectLoaded",
                    "id_objet": id_obj,
                    "meta": {"worker": "application-service"}
                }
                await producer.send_and_wait(TOPIC, json.dumps(loaded_evt).encode(), key=str(id_obj).encode())
                log.info("Application: published ObjectLoaded for %s", id_obj)
            except Exception as e:
                failed_evt = {
                    "event_type": "ObjectFailed",
                    "id_objet": id_obj,
                    "meta": {"worker": "application-service", "error": str(e)}
                }
                await producer.send_and_wait(TOPIC, json.dumps(failed_evt).encode(), key=str(id_obj).encode())
                log.exception("Application: failed processing %s", id_obj)
    finally:
        await consumer.stop()
        await producer.stop()
        log.info("application producer stopped")

if __name__ == "__main__":
    asyncio.run(run())
