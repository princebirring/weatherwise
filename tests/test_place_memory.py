"""Place memory on AgentCore Memory: what goes in and comes back (fake client, no AWS)."""

from weatherwise.agents.place_memory import SESSION, AgentCorePlaceMemory


class FakeMemoryClient:
    def __init__(self):
        self.events = []

    def create_event(self, memory_id, actor_id, session_id, messages):
        self.events.append({"memory_id": memory_id, "actor": actor_id, "session": session_id,
                            "payload": [{"conversational": {"content": {"text": t}, "role": r}} for t, r in messages]})

    def list_events(self, memory_id, actor_id, session_id, max_results):
        return [e for e in self.events if (e["memory_id"], e["actor"], e["session"]) == (memory_id, actor_id, session_id)]


def test_entries_round_trip_per_place_oldest_first():
    client = FakeMemoryClient()
    memory = AgentCorePlaceMemory("mem-1", client=client)
    memory.remember("place-a", {"day": "2026-11-03", "kind": "flood", "event_key": "k", "message": "पूर"})
    memory.remember("place-a", {"day": "2026-11-02", "kind": "flood", "event_key": "k", "message": "earlier"})
    memory.remember("place-b", {"day": "2026-11-03", "kind": "heat_dry", "event_key": "h", "message": "hot"})
    assert [e["day"] for e in memory.recall("place-a")] == ["2026-11-02", "2026-11-03"]
    assert memory.recall("place-a")[1]["message"] == "पूर"
    assert client.events[0]["session"] == SESSION and client.events[0]["payload"][0]["conversational"]["role"] == "ASSISTANT"
