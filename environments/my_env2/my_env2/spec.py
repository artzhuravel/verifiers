"""Reading the action spec — the one place that knows the spec's shape.

Everything downstream (the symbolic walker, the authoring prompts, replay) works from
`Action` objects rather than from raw JSON, so the spec's field names appear exactly once.
Nothing here knows this environment is a chat app.

Three distinctions carry the pipeline:

- **refs vs content.** A param that names an entity is a *ref*; the walker either binds it
  along an edge or mints a placeholder for it. Every other string param is *content* — text
  the environment does not constrain and the deterministic reward cannot see.
- **object vs value edges.** An `object` edge passes an entity id, so the effect it causes is
  visible in the state diff. A `value` edge passes read content into a downstream param, so
  only a judge can see whether the information actually made the trip.
- **external vs internal.** An external action (DeepWiki) has no state effect and a
  nondeterministic answer, so replay skips it and its content is authored, not observed.
"""

from dataclasses import dataclass, field
from typing import Any

# The two entity preconditions, and whether each names one entity or a list of them.
_ENTITY_PRECONDS = {"entity_exists": False, "entities_exist": True}

SLOT_KIND = {"object": "entity", "value": "info"}
"""Which produced kind a consumer slot accepts. An `object` slot takes an entity reference;
a `value` slot takes the content a read returned."""


@dataclass(frozen=True)
class Ref:
    """A param that names an entity rather than carrying content."""

    param: str
    entity_type: str
    many: bool
    """True when the param holds a list of ids (`entities_exist`)."""


@dataclass
class Action:
    id: str
    tool: str
    kind: str  # "read" | "write"
    description: str
    returns: str
    params: list[dict]
    refs: list[Ref]
    external: bool
    """No state effect and a nondeterministic result: replay skips it, authoring fills it."""
    produces: dict | None  # None = a sink
    consumes: list[dict]
    meaningful_when: list[dict]
    """Per-entity requirements that make this action worth performing at all (e.g. a chat
    with something actually unread). Not enforced by the tool; the authoring pass has to
    satisfy them, so they travel with the entity into the manifest."""

    @property
    def offer(self) -> tuple[str, str] | None:
        """What a completed action offers the next link, as (kind, type). None for a sink."""
        if not self.produces:
            return None
        return self.produces["kind"], self.produces["type"]

    def content_params(self) -> list[dict]:
        """String params the environment does not constrain — a message body, a chat's name, a
        repo question. Anything else is left at its default: a `limit` is not something the
        authoring model has a useful say in, and a `string[]` that is not already an entity ref
        would be minted as one placeholder and then passed where a list belongs."""
        refs = {ref.param for ref in self.refs}
        return [
            param
            for param in self.params
            if param["name"] not in refs and param["type"] == "string"
        ]


def parse_actions(spec: dict) -> list[Action]:
    parsed = []
    for entry in spec["actions"]:
        action_id = entry["id"]
        preconds = entry.get("preconditions", [])
        parsed.append(
            Action(
                id=action_id,
                tool=entry["tool"],
                kind=entry["kind"],
                description=entry["description"],
                returns=entry.get("returns", ""),
                params=entry.get("params", []),
                refs=[
                    Ref(
                        param=precond["ref"],
                        entity_type=precond["entity"],
                        many=_ENTITY_PRECONDS[precond["requires"]],
                    )
                    for precond in preconds
                    if precond["requires"] in _ENTITY_PRECONDS
                ],
                external=any(p["requires"] == "external_available" for p in preconds),
                produces=entry.get("produces"),
                consumes=entry.get("consumes", []),
                meaningful_when=entry.get("meaningful_when", []),
            )
        )
    return parsed


def consumer_index(
    actions: list[Action],
) -> dict[tuple[str, str], list[tuple[Action, dict]]]:
    """Offer type -> every (action, slot) that can take it. The walker's whole feasibility
    question is a lookup in here, which is what lets Stage 1 run without a world."""
    index: dict[tuple[str, str], list[tuple[Action, dict]]] = {}
    for action in actions:
        for consume in action.consumes:
            index.setdefault((SLOT_KIND[consume["slot"]], consume["type"]), []).append(
                (action, consume)
            )
    return index


@dataclass
class ReferenceMode:
    """One way of describing an entity instead of naming its id (see the spec's
    `reference_mode_semantics`). `params` are supplied by the authoring pass; the adapter
    turns (mode, params) into the set of entities that satisfy the predicate."""

    id: str
    entity_type: str
    params: list[dict]
    predicate: str
    phrase: str
    readable_via: list[str]

    def render(self, params: dict[str, Any]) -> str:
        """The mode as prose, for a prompt that must not name the id."""
        return self.phrase.format(**params)


def reference_modes(spec: dict) -> dict[str, list[ReferenceMode]]:
    return {
        entity_type: [
            ReferenceMode(
                id=mode["id"],
                entity_type=entity_type,
                params=mode.get("params", []),
                predicate=mode["predicate"],
                phrase=mode["phrase"],
                readable_via=mode.get("readable_via", []),
            )
            for mode in entry.get("reference_modes", [])
        ]
        for entity_type, entry in spec.get("entities", {}).items()
    }


@dataclass
class Slot:
    """A field the authoring pass has to fill, or a requirement it has to state.

    `content` slots are free text nothing constrains. `carry` slots are content too, but a
    value edge already decided what has to be in them — whatever an earlier step returned —
    so they become judge items rather than authored strings.
    """

    key: str  # step key
    param: str
    kind: str  # "content" | "carry"
    description: str
    sources: list[str] = field(default_factory=list)  # step keys, for a carry slot
