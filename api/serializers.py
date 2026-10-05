def experiment(e) -> dict:
    return {"id": e.id, "name": e.name, "productDescription": e.product_description, "targetAudience": e.target_audience,
            "researchObjectives": e.research_objectives, "createdAt": e.created_at.isoformat()}


def persona(p) -> dict:
    return {"id": p.id, "experimentId": p.experiment_id, "key": p.key, "name": p.name, "age": p.age, "occupation": p.occupation,
            "personality": p.personality, "behavioralPatterns": p.behavioral_patterns,
            "psychologicalProfile": p.psychological_profile, "segment": p.segment, "profile": p.profile}


def question(q) -> dict:
    return {"id": q.id, "questionId": q.key, "question": q.question, "type": q.type, "options": q.options,
            "scaleMin": q.scale_min, "scaleMax": q.scale_max, "order": q.order}
