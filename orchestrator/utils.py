import json
from pathlib import Path
from typing import List, Dict, Any

def load_objets(path: str) -> List[Dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
