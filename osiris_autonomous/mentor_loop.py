from osiris_ncllm.stream import stream

class MentorLoop:
    def __init__(self, student, mentor, challenger, critic, judge, memory, heretic=None):
        self.student = student
        self.mentor = mentor
        self.challenger = challenger
        self.critic = critic
        self.judge = judge
        self.memory = memory
        self.heretic = heretic

    def run(self, context, rounds=5):
        for i in range(rounds):
            stream.emit("THOUGHT:ROUND", str(i+1))
            # Instability injection
            if i % 5 == 0 and i > 0:
                self.student.exploration *= 1.5
            # Heretic agent (meta-disruption)
            used_heretic = False
            if self.heretic and random.random() < 0.2:
                disruption = self.heretic.propose(context, self.memory.history)
                stream.emit("HERETIC 🔥", disruption)
                context = disruption
                used_heretic = True
            q = self.student.generate_question(context)
            stream.emit("THOUGHT:QUESTION", q)
            a1 = self.mentor.respond(q)
            stream.emit("THOUGHT:ANSWER", a1)
            a2 = self.challenger.respond(q)
            stream.emit("THOUGHT:COUNTER", a2)
            c = self.critic.analyze(q, a1 + "\n" + a2)
            stream.emit("THOUGHT:CRITIQUE", c)
            r = self.student.reflect(q, a1 + "\n" + a2, c)
            stream.emit("THOUGHT:REFLECTION", r)
            score = self.judge.score(r)
            stream.emit("THOUGHT:JUDGE", f"Confidence: {score['confidence']}")
            self.student.adapt(score['confidence'])
            self.memory.update_identity(r, score)
            self.memory.store({
                "q": q,
                "a": a1 + "\n" + a2,
                "critique": c,
                "reflection": r,
                "score": score,
                "source": "heretic" if used_heretic else "mentor",
                "context": context
            })
            self.mentor.update_trust(score["confidence"])
            self.challenger.update_trust(score["confidence"])
            # Adaptive context/goals
            if score["confidence"] > 0.8:
                context = f"advance beyond: {context}"
            elif score["confidence"] < 0.4:
                context = f"relearn fundamentals of: {context}"
        self.memory.save()
