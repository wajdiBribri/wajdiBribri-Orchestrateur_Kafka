from pydantic import BaseModel
from typing import Optional, Dict, Any

class OrchestratorEvent(BaseModel):
    event_type: str  # ObjectReady, ObjectLoaded, ObjectFailed
    id_objet: int
    meta: Optional[Dict[str, Any]] = None
