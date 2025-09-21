from prometheus_client import Counter, start_http_server

# compteur pour tous les événements publiés
# label "status" = type d'événement, label "producer" = microservice source
EVENTS_PUBLISHED = Counter(
    "events_published_total",
    "Total events published by orchestrator and producers",
    ["status", "producer"]
)

# démarrer le serveur metrics pour Prometheus
start_http_server(8001)  # Prometheus scrape sur http://localhost:8001/metrics
