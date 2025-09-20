import asyncio
import json
import os
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

log = logging.getLogger("producer_standardize")
logging.basicConfig(level=logging.INFO)

KAFKA = os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")
TOPIC = "object.events"

# tranche standardize (milieu)
MIN_ID = 2000
MAX_ID = 2999

async def run():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA,
        group_id="standardize-service",
        auto_offset_reset="latest",
        enable_auto_commit=True,
    )
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA)
    await consumer.start()
    await producer.start()
    log.info("standardize producer started")
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

            if not (MIN_ID <= id_obj <= MAX_ID):
                continue

            log.info("Standardize: handling id %s", id_obj)

            if id_obj == 2005:
                failed_evt = {
                    "event_type": "ObjectFailed",
                    "id_objet": id_obj,
                    "meta": {"worker": "standardize-service", "error":"test forcé de objectfailed"}
                }
                await producer.send_and_wait(TOPIC, json.dumps(failed_evt).encode(), key=str(id_obj).encode())
                log.exception("Standardize: failed processing %s", id_obj)
            # simulate transform/standardize work (could be CPU or IO bound)
            try:
                await asyncio.sleep(0.6)
                # TODO: ici placer la logique de transformation réelle
                loaded_evt = {
                    "event_type": "ObjectLoaded",
                    "id_objet": id_obj,
                    "meta": {"worker": "standardize-service"}
                }
                await producer.send_and_wait(TOPIC, json.dumps(loaded_evt).encode(), key=str(id_obj).encode())
                log.info("Standardize: published ObjectLoaded for %s", id_obj)
            except Exception as e:
                failed_evt = {
                    "event_type": "ObjectFailed",
                    "id_objet": id_obj,
                    "meta": {"worker": "standardize-service", "error": str(e)}
                }
                await producer.send_and_wait(TOPIC, json.dumps(failed_evt).encode(), key=str(id_obj).encode())
                log.exception("Standardize: failed processing %s", id_obj)
    finally:
        await consumer.stop()
        await producer.stop()
        log.info("standardize producer stopped")

if __name__ == "__main__":
    asyncio.run(run())
