import secrets

from santa.schemas import EventData


def allowed_recipients(data: EventData) -> dict[str, list[str]]:
    ids = [str(person.id) for person in data.participants]
    blocked = {person: {person} for person in ids}
    for group in data.groups:
        members = {str(member) for member in group.members}
        for member in members:
            blocked[member].update(members)
    return {person: [other for other in ids if other not in blocked[person]] for person in ids}


def matching(data: EventData, *, randomize: bool = False) -> dict[str, str] | None:
    if len(data.participants) < 2:
        return None
    edges = allowed_recipients(data)
    givers = list(edges)
    if randomize:
        rng = secrets.SystemRandom()
        rng.shuffle(givers)
        for candidates in edges.values():
            rng.shuffle(candidates)
    owners: dict[str, str] = {}

    def augment(giver: str, seen: set[str]) -> bool:
        for recipient in edges[giver]:
            if recipient in seen:
                continue
            seen.add(recipient)
            if recipient not in owners or augment(owners[recipient], seen):
                owners[recipient] = giver
                return True
        return False

    for giver in givers:
        if not augment(giver, set()):
            return None
    return {giver: recipient for recipient, giver in owners.items()}


def feasibility(data: EventData) -> dict:
    if len(data.participants) < 2:
        return {"possible": False, "message": "Ajoutez au moins 2 participants (maximum 200)."}
    edges = allowed_recipients(data)
    stranded = [person.name for person in data.participants if not edges[str(person.id)]]
    if stranded:
        return {
            "possible": False,
            "message": "Aucun destinataire autorisé pour : " + ", ".join(stranded),
        }
    if matching(data) is None:
        return {
            "possible": False,
            "message": (
                "Les exclusions ne permettent pas que chacun reçoive exactement un cadeau. "
                "Réduisez les groupes ou ajoutez des participants hors de ces groupes."
            ),
        }
    return {
        "possible": True,
        "message": "Configuration possible : chacun donnera et recevra un cadeau.",
    }
