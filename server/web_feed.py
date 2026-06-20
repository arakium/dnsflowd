from typing import List, Dict, Any
import bridge

def consume_live_feeds() -> List[Dict[str, Any]]:
    batch = []
    while not bridge.live_traffic_queue.empty():
        batch.append(bridge.live_traffic_queue.get_nowait())
    return batch
