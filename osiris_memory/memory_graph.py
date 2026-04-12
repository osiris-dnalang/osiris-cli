class MemoryGraph:
    """
    Simple graph-based memory for storing and retrieving text nodes with connections.
    """
    def __init__(self):
        self.nodes = []
        self.edges = {}
    def add(self, text):
        self.nodes.append(text)
        self.edges[text] = []
    def connect(self, a, b):
        self.edges[a].append(b)
    def retrieve(self, query):
        results = []
        for node in self.nodes:
            if query in node:
                results.append(node)
        return results[:3]
