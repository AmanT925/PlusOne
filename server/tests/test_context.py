from contracts.schema import Constraint, Event
from server.context import context_for, public_model_inputs


def _events():
    return [
        Event(1, 1.0, "sam", "public", "let's do the fancy resort"),
        Event(2, 2.0, "sam", "private:sam", "I can't do more than 150 this month"),
        Event(3, 3.0, "priya", "private:priya", "I cannot be in a room with Alex"),
        Event(4, 4.0, "priya", "public", "maybe next weekend"),
    ]


def _constraints():
    return [
        Constraint("sam", "budget_cap", "150", True),
        Constraint("priya", "avoid_person", "Alex", True),
    ]


def test_context_for_hides_other_private_events():
    def summarize(constraints):
        assert all(isinstance(c.user, str) for c in constraints)
        return "budget ceiling is about $150"

    ctx = context_for("sam", _events(), _constraints(), summarize)
    assert [e.text for e in ctx.public_log] == [
        "let's do the fancy resort",
        "maybe next weekend",
    ]
    assert [e.text for e in ctx.own_private_events] == [
        "I can't do more than 150 this month"
    ]
    leaked = " ".join(e.text for e in ctx.own_private_events + ctx.public_log)
    assert "cannot be in a room with Alex" not in leaked
    assert ctx.group_summary == "budget ceiling is about $150"


def test_public_model_inputs_have_no_private_events():
    public_log, summary = public_model_inputs(
        _events(), _constraints(), lambda _c: "anonymous"
    )
    assert all(e.visibility == "public" for e in public_log)
    assert summary == "anonymous"
