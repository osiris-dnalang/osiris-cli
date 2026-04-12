def active_agents(H):
    if H < 0.3:
        return ["student", "mentor", "judge"]
    elif H > 1.2:
        return ["student", "critic"]
    return ["student", "mentor", "critic", "judge"]
