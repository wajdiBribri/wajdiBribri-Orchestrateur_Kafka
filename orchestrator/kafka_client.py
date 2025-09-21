from aiokafka import AIOKafkaConsumer
import json
import logging

log = logging.getLogger("kafka_client")

class KafkaClient:
    def __init__(self, bootstrap_servers="kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self._producer = None

    async def start(self):
        if self._producer is None:
            from aiokafka import AIOKafkaProducer
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
            await self._producer.start()
            log.info("Kafka producer started (%s)", self.bootstrap_servers)

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
            log.info("Kafka producer stopped")

    async def publish(self, topic: str, value: dict, key=None):
        if self._producer is None:
            raise RuntimeError("Producer not started")
        key_bytes = None if key is None else (key if isinstance(key, bytes) else str(key).encode("utf-8"))
        payload = json.dumps(value).encode("utf-8")
        await self._producer.send_and_wait(topic, payload, key=key_bytes)
        log.debug("Published event to %s key=%s value=%s", topic, key, value)

    # --- Nouvelle méthode pour consommer un batch ---
    async def consume_batch(self, topic, max_records=10, timeout_ms=500):
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id="orchestrator-consumer",
            auto_offset_reset="latest",
            enable_auto_commit=True
        )
        await consumer.start()
        try:
            msgs = await consumer.getmany(timeout_ms=timeout_ms, max_records=max_records)
            events = []
            for tp, batch in msgs.items():
                for msg in batch:
                    try:
                        events.append(json.loads(msg.value.decode()))
                    except Exception:
                        continue
            return events
        finally:
            await consumer.stop()
