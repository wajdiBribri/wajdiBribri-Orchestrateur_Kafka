import json
import logging
from aiokafka import AIOKafkaProducer

log = logging.getLogger("kafka_client")
logging.basicConfig(level=logging.INFO)

class KafkaClient:
    def __init__(self, bootstrap_servers="kafka:9092"):
        self.bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def start(self):
        if self._producer is None:
            self._producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
            await self._producer.start()
            log.info("Kafka producer started (%s)", self.bootstrap_servers)

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
            log.info("Kafka producer stopped")

    async def publish(self, topic: str, value: dict, key=None):
        """
        Publie un événement JSON sur Kafka.
        key peut être None, int, str ou bytes.
        """
        if self._producer is None:
            raise RuntimeError("Producer not started")
        # normalize key to bytes if provided
        if key is None:
            key_bytes = None
        elif isinstance(key, bytes):
            key_bytes = key
        else:
            key_bytes = str(key).encode("utf-8")

        try:
            payload = json.dumps(value).encode("utf-8")
            await self._producer.send_and_wait(topic, payload, key=key_bytes)
            log.debug("Published event to %s key=%s value=%s", topic, key, value)
        except Exception as e:
            log.exception("Failed to publish to %s: %s", topic, e)
            raise
