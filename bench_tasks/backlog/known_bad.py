"""backlog -- a tiny story backlog."""


class Backlog:
    # Plausible but breaks the API: dedupes via a new method and drops set_status.
    def __init__(self):
        self.stories = []
        self.next_id = 1

    def add(self, text, source="manual"):
        if any(s["text"] == text for s in self.stories):
            return None
        story = {"id": self.next_id, "text": text, "source": source, "status": "backlog"}
        self.stories.append(story)
        self.next_id += 1
        return story["id"]

    def open_stories(self):
        return [s for s in self.stories if s["status"] in ("backlog", "active")]
