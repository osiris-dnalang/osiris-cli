class TetrahedralField:
    def __init__(self, ndim=4):
        # State: [q, a, c, j] for each dimension
        self.state = [0.0] * ndim
        self.history = []
        self.beta = 0.5

    def step(self, beta=None):
        if beta is not None:
            self.beta = beta
        # Simple recursive update: q->a->c->j->q'
        q, a, c, j = self.state[:4]
        # Mentor ensemble (simulate disagreement)
        mentors = [a + 0.1, a - 0.1, a]
        a_new = sum(mentors) / len(mentors)
        c_new = abs(q - a_new)  # constraint
        j_new = 1.0 if c_new < 0.05 else 0.0  # judge
        q_new = q + self.beta * (a_new - q) - 0.1 * c_new
        self.state = [q_new, a_new, c_new, j_new]
        self.history.append(tuple(self.state))

    def summary(self):
        keys = ['q', 'a', 'c', 'j']
        return {k: round(v, 4) for k, v in zip(keys, self.state)}

def main():
    tf = TetrahedralField()

    for epoch in range(10):
        tf.step(beta=0.5)
        summary = tf.summary()
        print(f"\n⚛ Epoch {epoch}")
        for k, v in summary.items():
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
