"""backlog -- a tiny story backlog."""


class Backlog:
    def __init__(self):
        self.stories = []
        self.next_id = 1

    def add(self, text, source="manual"):
        story = {"id": self.next_id, "text": text, "source": source, "status": "backlog"}
        self.stories.append(story)
        self.next_id += 1
        return story["id"]

    def set_status(self, story_id, status):
        for s in self.stories:
            if s["id"] == story_id:
                s["status"] = status
                return True
        return False

    def open_stories(self):
        return [s for s in self.stories if s["status"] in ("backlog", "active")]
