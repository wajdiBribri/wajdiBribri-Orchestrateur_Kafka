import asyncio
from datetime import datetime
import json
import networkx as nx
from typing import List, Set
import requests

from .utils import load_objets
from .models import OrchestratorEvent
from .kafka_client import KafkaClient
from .metrics import EVENTS_PUBLISHED


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


class Orchestrator:
    def __init__(self, objets_path: str, kafka_client: KafkaClient, topic="object.events"):
        self.objets_path = objets_path
        self.kafka = kafka_client
        self.topic = topic
        self.graph = nx.DiGraph()
        self.nodes_meta = {}

    def build_graph(self):
        data = load_objets(self.objets_path)
        self.graph.clear()
        self.nodes_meta.clear()

        for o in data:
            node_id = int(o["IdObjet"])
            self.graph.add_node(node_id)
            self.nodes_meta[node_id] = o

        for o in data:
            child = int(o["IdObjet"])
            parents = o.get("IdObjet_Parent")
            if not parents:
                continue
            if isinstance(parents, str):
                for par in [p.strip() for p in parents.split(",") if p.strip().isdigit()]:
                    self.graph.add_edge(int(par), child)
            elif isinstance(parents, (int, float)):
                self.graph.add_edge(int(parents), child)

    def extract_subgraph(self, final_prefix=3000) -> nx.DiGraph:
        finals = [n for n, m in self.nodes_meta.items() if int(n) >= final_prefix]
        nodes_needed: Set[int] = set()
        for f in finals:
            if f in self.graph:
                nodes_needed |= nx.ancestors(self.graph, f)
                nodes_needed.add(f)
        return self.graph.subgraph(nodes_needed).copy()

    def topo_order(self, subgraph: nx.DiGraph) -> List[int]:
        try:
            return list(nx.topological_sort(subgraph))
        except nx.NetworkXUnfeasible:
            cycles = list(nx.simple_cycles(subgraph))
            for cycle in cycles:
                subgraph.remove_edge(cycle[-1], cycle[0])
            return list(nx.topological_sort(subgraph))

    async def publish_ready_events(self, order: List[int]):
        for node in order:
            evt = OrchestratorEvent(
                event_type="ObjectReady",
                id_objet=node,
                meta=self.nodes_meta.get(node),
                event_datetime=datetime.now()
            )
            evt_dict = evt.dict()
            evt_dict["event_datetime"] = evt.event_datetime.isoformat()

            await self.kafka.publish(self.topic, evt_dict, str(node).encode())
            EVENTS_PUBLISHED.labels(status=evt.event_type, producer="orchestrator").inc()
            log_event_to_loki(evt_dict, producer="orchestrator")
            await asyncio.sleep(0.01)

    async def run_once(self):
        self.build_graph()
        sub = self.extract_subgraph()
        order = self.topo_order(sub)
        await self.publish_ready_events(order)
        return order
    def to_dict(self, subgraph=None):
        """
        Retourne le graphe sous forme JSON sérialisable :
        { "nodes": [...], "edges": [...] }
        """
        g = subgraph or self.graph
        nodes = []
        for n in g.nodes:
            meta = self.nodes_meta.get(n, {})
            nodes.append({
                "id": n,
                "label": meta.get("NomObjet", f"Obj{n}"),
                "type": self._infer_type(n)
            })
        edges = [{"source": u, "target": v} for u, v in g.edges]
        return {"nodes": nodes, "edges": edges}

    def _infer_type(self, node_id: int) -> str:
        if node_id >= 3000:
            return "application"
        elif node_id >= 2000:
            return "standardize"
        else:
            return "ingest"
    
    def to_dot(self, subgraph=None) -> str:
        g = subgraph or self.graph
        return nx.nx_pydot.to_pydot(g).to_string()
