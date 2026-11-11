"""The leaf lifecycle as a pure reducer (F-903, F-905, F-907, F-919).

Rows Y-1 to Y-24 of `docs/acceptance/08-ticks-formatters-lifecycle.md`: one test per
cell of ADR 0001 §4's table, and the overlapping cases of ADR 0003 §5's precedence. The
expected states and actions are the table's, written out here.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from manim_plots.core.lifecycle import (
    Action,
    Become,
    Begin,
    Copy,
    DataChange,
    Ending,
    Finish,
    FrameMoved,
    Kind,
    Leaf,
    Read,
    Rebind,
    Refresh,
    ReversePoints,
    State,
    SuspendUpdating,
    Write,
    Writer,
    transition,
)

A, T, R, S = State.ATTACHED, State.TRANSIENT, State.REMOVED, State.SHAPED


def leaf_in(state: State) -> Leaf:
    """A leaf in ``state``; a transient one has one owner and came from A."""
    if state is T:
        return Leaf(state=T, owners=("anim",), origin=A)
    return Leaf(state=state)


def kinds(actions) -> list[Kind]:
    return [a.kind for a in actions]


def cell(state: State, event) -> tuple[Leaf, list[Kind]]:
    after, actions = transition(leaf_in(state), event)
    return after, kinds(actions)


# --- Y-1 to Y-6: reads and writes --------------------------------------------------

READS_AND_WRITES = [
    (
        Read(),
        {
            A: [Kind.REBUILD_IF_DIRTY],
            T: [Kind.READ_BUFFER],
            R: [Kind.READ_BUFFER],
            S: [Kind.READ_SHAPE],
        },
    ),
    (
        Write(Writer.FRAME),
        {
            A: [Kind.IGNORE],
            T: [Kind.WRITE_BUFFER],
            R: [Kind.WRITE_BUFFER],
            S: [Kind.IGNORE],
        },
    ),
    (
        Write(Writer.OTHER),
        {
            A: [Kind.OWN_TRANSFORM],
            T: [Kind.WRITE_BUFFER],
            R: [Kind.WRITE_BUFFER],
            S: [Kind.TRANSFORM_SHAPE],
        },
    ),
    (
        Write(Writer.BARE),
        {
            A: [Kind.KEEP_UNTIL_REBUILD],
            T: [Kind.WRITE_BUFFER],
            R: [Kind.WRITE_BUFFER],
            S: [Kind.KEEP_UNTIL_REBUILD],
        },
    ),
    (
        ReversePoints(),
        {
            A: [Kind.TOGGLE_DIRECTION],
            T: [Kind.WRITE_BUFFER],
            R: [Kind.REVERSE_BUFFER],
            S: [Kind.REVERSE_SHAPE],
        },
    ),
]


@pytest.mark.parametrize("state", [A, T, R, S], ids=lambda s: s.value)
@pytest.mark.parametrize(
    "event, expected",
    READS_AND_WRITES,
    ids=lambda e: type(e).__name__ if not isinstance(e, dict) else "",
)
def test_y1_to_y6_reads_and_writes_keep_the_state(state, event, expected):
    before = leaf_in(state)
    after, actions = transition(before, event)
    assert kinds(actions) == expected[state]
    assert after == before


def test_y2_a_data_change_marks_an_attached_leaf_dirty():
    assert cell(A, DataChange())[1] == [Kind.MARK_DIRTY]


def test_y2_a_data_change_during_an_animation_is_deferred():
    after, actions = cell(T, DataChange())
    assert actions == []
    assert after.deferred == (DataChange(),)
    assert after.state is T


@pytest.mark.parametrize("state", [R, S], ids=lambda s: s.value)
def test_y2_a_detached_leaf_ignores_data(state):
    after, actions = cell(state, DataChange())
    assert actions == [Kind.IGNORE]
    assert after.state is state


# --- Y-7: an animation begins --------------------------------------------------------


def test_y7_attached_becomes_transient_with_one_owner():
    after, actions = transition(Leaf(), Begin("fade"))
    assert actions == ()
    assert (after.state, after.owners, after.origin) == (T, ("fade",), A)


def test_y7_a_second_owner_is_added():
    after, actions = transition(leaf_in(T), Begin("second"))
    assert actions == ()
    assert after.owners == ("anim", "second")
    assert after.origin is A


@pytest.mark.parametrize("state", [R, S], ids=lambda s: s.value)
def test_y7_an_introducer_reattaches_and_retakes_its_start(state):
    after, actions = transition(Leaf(state=state), Begin("create", introducer=True))
    assert kinds(actions) == [Kind.REATTACH, Kind.RETAKE_START]
    assert (after.state, after.owners, after.origin) == (T, ("create",), A)


@pytest.mark.parametrize("state", [R, S], ids=lambda s: s.value)
def test_y7_another_animation_keeps_the_detached_origin(state):
    after, actions = transition(Leaf(state=state), Begin("wiggle"))
    assert actions == ()
    assert (after.state, after.origin) == (T, state)


def test_y20_beginning_twice_with_one_owner_raises():
    with pytest.raises(ValueError):
        transition(leaf_in(T), Begin("anim"))


# --- Y-8 to Y-14 ---------------------------------------------------------------------


def test_y8_refresh():
    assert cell(A, Refresh()) == (Leaf(), [Kind.REBUILD])
    after, actions = cell(T, Refresh())
    assert actions == [] and after.deferred == (Refresh(),)
    for state in (R, S):
        after, actions = cell(state, Refresh())
        assert actions == [Kind.REATTACH]
        assert after.state is A


def test_y9_become_an_artist():
    for state in (A, R, S):
        after, actions = transition(leaf_in(state), Become("other", artist=True))
        assert actions == (Action(Kind.ADOPT, "other"),)
        assert after.state is A
    during = Leaf(state=T, owners=("anim",), origin=S, target=(Ending.PLAIN, "p"))
    after, actions = transition(during, Become("other", artist=True))
    assert actions == (Action(Kind.ADOPT, "other"), Action(Kind.CANCEL_TARGETS))
    assert (after.state, after.origin, after.cancelled, after.target) == (
        T,
        A,
        True,
        None,
    )
    assert after.owners == ("anim",)


def test_y10_become_a_plain_mobject():
    for state in (A, R, S):
        after, actions = transition(leaf_in(state), Become("square", artist=False))
        assert actions == (Action(Kind.SHAPE_FROM_TARGET, "square"),)
        assert after.state is S
    after, actions = transition(leaf_in(T), Become("square", artist=False))
    assert actions == (Action(Kind.SHAPE_FROM_TARGET, "square"),)
    assert (after.state, after.origin, after.owners) == (T, S, ("anim",))


@pytest.mark.parametrize(
    "state, kind",
    [
        (A, Kind.COPY_ATTACHED),
        (T, Kind.COPY_REBUILT),
        (R, Kind.COPY_REMOVED),
        (S, Kind.COPY_SHAPED),
    ],
    ids=["A", "T", "R", "S"],
)
def test_y11_copy_leaves_the_original_alone(state, kind):
    before = leaf_in(state)
    after, actions = transition(before, Copy())
    assert kinds(actions) == [kind]
    assert after == before


def test_y12_suspend_updating_outside_an_animation():
    assert cell(A, SuspendUpdating())[1] == [Kind.PAUSE_UPDATERS]
    for state in (T, R, S):
        after, actions = cell(state, SuspendUpdating())
        assert actions == [] and after == leaf_in(state)


def test_y13_the_frame_moves():
    assert cell(A, FrameMoved())[1] == [Kind.FOLLOW_FRAME]
    assert cell(T, FrameMoved())[1] == [Kind.COPIES_FOLLOW]
    assert cell(R, FrameMoved())[1] == []
    assert cell(S, FrameMoved())[1] == [Kind.FOLLOW_FRAME]


def test_y14_replacement_transform_rebinds():
    for state in (A, S):
        after, actions = transition(leaf_in(state), Rebind("new_ax"))
        assert actions == (Action(Kind.REBIND, "new_ax"),)
        assert after.state is state
    deferred, kinds = cell(T, Rebind("new_ax"))
    assert kinds == [] and deferred.deferred == (Rebind("new_ax"),)
    removed, kinds = cell(R, Rebind("new_ax"))
    assert kinds == [] and removed == leaf_in(R)


# --- Y-20 to Y-23: finishing ---------------------------------------------------------


def finish(
    leaf: Leaf, owner="anim", ending=Ending.ELSEWHERE, target=None, remover=False
):
    return transition(leaf, Finish(owner, ending, target, remover))


def assert_left_transient(leaf: Leaf, state: State) -> None:
    assert leaf.state is state
    assert leaf.owners == () and leaf.origin is None and leaf.target is None
    assert leaf.cancelled is False and leaf.deferred == ()


@pytest.mark.parametrize("state", [A, R, S], ids=lambda s: s.value)
def test_y20_finishing_outside_an_animation_raises(state):
    with pytest.raises(ValueError):
        finish(Leaf(state=state))


def test_y20_finishing_an_animation_that_does_not_own_the_leaf_raises():
    with pytest.raises(ValueError):
        finish(leaf_in(T), owner="stranger")


def test_y21_an_owner_finishing_early_records_its_target():
    two = Leaf(state=T, owners=("a", "b"), origin=A)
    after, actions = finish(two, owner="a", ending=Ending.ARTIST, target="x")
    assert actions == ()
    assert after.owners == ("b",) and after.target == (Ending.ARTIST, "x")
    again, _ = finish(
        Leaf(state=T, owners=("a", "b", "c"), origin=A, target=(Ending.ARTIST, "x")),
        owner="a",
        ending=Ending.PLAIN,
        target="y",
    )
    assert again.target == (Ending.PLAIN, "y")


def test_y21_an_early_owner_without_a_target_keeps_the_recorded_one():
    two = Leaf(state=T, owners=("a", "b"), origin=A, target=(Ending.ARTIST, "x"))
    after, _ = finish(two, owner="a", ending=Ending.START)
    assert after.target == (Ending.ARTIST, "x")


def test_y22_rule_1_a_remover_freezes():
    after, actions = finish(leaf_in(T), remover=True)
    assert kinds(actions) == [Kind.FREEZE]
    assert_left_transient(after, R)


def test_y22_rule_3_an_artist_target_is_adopted():
    after, actions = finish(leaf_in(T), ending=Ending.ARTIST, target="x")
    assert actions == (Action(Kind.ADOPT, "x"),)
    assert_left_transient(after, A)


def test_y22_rule_4_a_plain_target_shapes_the_leaf():
    after, actions = finish(leaf_in(T), ending=Ending.PLAIN, target="square")
    assert actions == (Action(Kind.SHAPE_FROM_TARGET, "square"),)
    assert_left_transient(after, S)


@pytest.mark.parametrize(
    "origin, kind",
    [(A, Kind.REBUILD), (S, Kind.USE_SHAPE), (R, Kind.FREEZE)],
    ids=["A", "S", "R"],
)
def test_y22_rule_5_ending_on_the_start_returns_to_the_origin(origin, kind):
    after, actions = finish(
        Leaf(state=T, owners=("anim",), origin=origin), ending=Ending.START
    )
    assert kinds(actions) == [kind]
    assert_left_transient(after, origin)


def test_y22_rule_6_ending_elsewhere_without_a_target_shapes_from_the_buffer():
    after, actions = finish(leaf_in(T), ending=Ending.ELSEWHERE)
    assert kinds(actions) == [Kind.SHAPE_FROM_BUFFER]
    assert_left_transient(after, S)


def test_y23_deferred_events_apply_in_order_after_finishing():
    during = Leaf(
        state=T,
        owners=("anim",),
        origin=A,
        deferred=(DataChange(), Refresh(), DataChange()),
    )
    after, actions = finish(during, ending=Ending.START)
    assert kinds(actions) == [
        Kind.REBUILD,
        Kind.MARK_DIRTY,
        Kind.REBUILD,
        Kind.MARK_DIRTY,
    ]
    assert_left_transient(after, A)


def test_y23_a_deferred_rebind_applies_after_the_last_owner():
    during = Leaf(state=T, owners=("anim",), origin=A, deferred=(Rebind("new_ax"),))
    _, actions = finish(during, ending=Ending.ARTIST, target="x")
    assert actions == (Action(Kind.ADOPT, "x"), Action(Kind.REBIND, "new_ax"))


def test_y24_an_unknown_event_raises_type_error():
    @dataclass(frozen=True)
    class Unknown:
        pass

    with pytest.raises(TypeError):
        transition(Leaf(), Unknown())  # type: ignore[arg-type]


# --- ADR 0003 §5: overlapping rules ---------------------------------------------------


def test_overlap_a_remover_that_ended_on_an_artist_target_is_removed():
    after, actions = finish(leaf_in(T), ending=Ending.ARTIST, target="x", remover=True)
    assert kinds(actions) == [Kind.FREEZE]
    assert after.state is R


def test_overlap_become_cancels_a_target_reached_later():
    leaf, _ = transition(leaf_in(T), Become("other", artist=True))
    after, actions = finish(leaf, ending=Ending.ARTIST, target="x")
    assert Action(Kind.ADOPT, "x") not in actions
    assert kinds(actions) == [Kind.SHAPE_FROM_BUFFER]
    assert after.state is S


def test_overlap_become_then_ending_on_the_start_returns_to_the_adopted_artist():
    leaf, _ = transition(leaf_in(T), Become("other", artist=True))
    after, actions = finish(leaf, ending=Ending.START)
    assert kinds(actions) == [Kind.REBUILD]
    assert after.state is A


def test_overlap_two_targets_the_last_to_finish_wins():
    leaf = Leaf(state=T, owners=("a", "b"), origin=A)
    leaf, _ = finish(leaf, owner="a", ending=Ending.ARTIST, target="first")
    after, actions = finish(leaf, owner="b", ending=Ending.PLAIN, target="second")
    assert actions == (Action(Kind.SHAPE_FROM_TARGET, "second"),)
    assert after.state is S


def test_overlap_an_earlier_target_is_adopted_when_the_last_owner_ends_elsewhere():
    leaf = Leaf(state=T, owners=("a", "b"), origin=A)
    leaf, _ = finish(leaf, owner="a", ending=Ending.ARTIST, target="first")
    after, actions = finish(leaf, owner="b", ending=Ending.ELSEWHERE)
    assert actions == (Action(Kind.ADOPT, "first"),)
    assert after.state is A


def test_overlap_a_remover_with_a_deferred_refresh_ends_attached():
    leaf = Leaf(state=T, owners=("anim",), origin=A, deferred=(Refresh(),))
    after, actions = finish(leaf, remover=True)
    assert kinds(actions) == [Kind.FREEZE, Kind.REATTACH]
    assert after.state is A


def test_overlap_deferred_data_after_a_remover_is_ignored():
    leaf = Leaf(state=T, owners=("anim",), origin=A, deferred=(DataChange(),))
    after, actions = finish(leaf, remover=True)
    assert kinds(actions) == [Kind.FREEZE, Kind.IGNORE]
    assert after.state is R


def test_f907_create_after_uncreate_draws_the_current_curve():
    leaf, _ = transition(Leaf(), Begin("uncreate"))
    leaf, actions = finish(leaf, owner="uncreate", remover=True)
    assert leaf.state is R and kinds(actions) == [Kind.FREEZE]
    leaf, actions = transition(leaf, Begin("create", introducer=True))
    assert kinds(actions) == [Kind.REATTACH, Kind.RETAKE_START]
    leaf, actions = finish(leaf, owner="create", ending=Ending.START)
    assert kinds(actions) == [Kind.REBUILD]
    assert leaf.state is A
