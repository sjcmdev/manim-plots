"""Reduce leaf lifecycle events to immutable state and ordered actions."""

from __future__ import annotations

from collections.abc import Hashable
from dataclasses import dataclass, replace
from enum import Enum, auto


class State(Enum):
    """Enumerate attached, transient, removed and shaped leaf states."""

    ATTACHED = "A"
    TRANSIENT = "T"
    REMOVED = "R"
    SHAPED = "S"


class Writer(Enum):
    """Identify a frame container, another container or a bare array write."""

    FRAME = "frame"
    OTHER = "other"
    BARE = "bare"


class Ending(Enum):
    """Classify an animation's final buffer relative to its targets and start."""

    ARTIST = "artist"
    PLAIN = "plain"
    START = "start"
    ELSEWHERE = "elsewhere"


class Kind(Enum):
    """Enumerate actions performed by the Manim layer after a transition."""

    REBUILD_IF_DIRTY = auto()
    READ_BUFFER = auto()
    READ_SHAPE = auto()
    MARK_DIRTY = auto()
    IGNORE = auto()
    OWN_TRANSFORM = auto()
    KEEP_UNTIL_REBUILD = auto()
    WRITE_BUFFER = auto()
    TRANSFORM_SHAPE = auto()
    TOGGLE_DIRECTION = auto()
    REVERSE_BUFFER = auto()
    REVERSE_SHAPE = auto()
    REATTACH = auto()
    RETAKE_START = auto()
    ADOPT = auto()
    REBUILD = auto()
    USE_SHAPE = auto()
    FREEZE = auto()
    SHAPE_FROM_TARGET = auto()
    SHAPE_FROM_BUFFER = auto()
    CANCEL_TARGETS = auto()
    PAUSE_UPDATERS = auto()
    FOLLOW_FRAME = auto()
    COPIES_FOLLOW = auto()
    REBIND = auto()
    COPY_ATTACHED = auto()
    COPY_REBUILT = auto()
    COPY_REMOVED = auto()
    COPY_SHAPED = auto()


@dataclass(frozen=True)
class Action:
    """Describe one action and its optional referenced object identity.

    Parameters
    ----------
    kind
        Action to execute.
    ref
        Target, artist or system identity used by the action.
    """

    kind: Kind
    ref: Hashable | None = None


@dataclass(frozen=True)
class Read:
    """Request a leaf's points or bounds."""


@dataclass(frozen=True)
class DataChange:
    """Notify a leaf that its data or range changed."""


@dataclass(frozen=True)
class Write:
    """Classify a write to the leaf's points.

    Parameters
    ----------
    writer
        Writer's relation to the system frame.
    """

    writer: Writer


@dataclass(frozen=True)
class ReversePoints:
    """Reverse the order in which a leaf's geometry is traversed."""


@dataclass(frozen=True)
class Begin:
    """Give an animation ownership of the leaf's buffer.

    Parameters
    ----------
    owner
        Animation identity, unique among current owners.
    introducer
        Whether the animation reattaches a detached leaf before beginning.
    """

    owner: Hashable
    introducer: bool = False


@dataclass(frozen=True)
class Finish:
    """Release one animation's ownership after its cleanup.

    Parameters
    ----------
    owner
        Current animation identity.
    ending
        Final relation to the animation's targets or starting copy.
    target
        Artist or plain-target identity, when applicable.
    remover
        Whether the finishing animation removes the leaf.
    """

    owner: Hashable
    ending: Ending
    target: Hashable | None = None
    remover: bool = False


@dataclass(frozen=True)
class Refresh:
    """Reattach a detached leaf or rebuild an attached one."""


@dataclass(frozen=True)
class Become:
    """Adopt another artist or retain a plain target's shape.

    Parameters
    ----------
    other
        Identity of the adopted object.
    artist
        Whether the target is a library artist rather than plain geometry.
    """

    other: Hashable
    artist: bool


@dataclass(frozen=True)
class Copy:
    """Request an unregistered copy without changing the original leaf."""


@dataclass(frozen=True)
class SuspendUpdating:
    """Suspend updating when no animation owns the call."""


@dataclass(frozen=True)
class FrameMoved:
    """Notify a leaf that its system's frame moved."""


@dataclass(frozen=True)
class Rebind:
    """Transfer a registered leaf to a replacement system.

    Parameters
    ----------
    system
        Identity of the replacement system.
    """

    system: Hashable


type Event = (
    Read
    | DataChange
    | Write
    | ReversePoints
    | Begin
    | Finish
    | Refresh
    | Become
    | Copy
    | SuspendUpdating
    | FrameMoved
    | Rebind
)


@dataclass(frozen=True)
class Leaf:
    """Hold lifecycle state independently of Manim geometry.

    Parameters
    ----------
    state
        Current lifecycle state.
    owners
        Running animations in begin order.
    origin
        State to restore when the last animation returns to its start.
    target
        Latest artist or plain target recorded by a finished owner.
    cancelled
        Whether becoming an artist cancelled animation targets.
    deferred
        Data changes, refreshes and rebinds awaiting the last owner's finish.
    """

    state: State = State.ATTACHED
    owners: tuple[Hashable, ...] = ()
    origin: State | None = None
    target: tuple[Ending, Hashable] | None = None
    cancelled: bool = False
    deferred: tuple[Event, ...] = ()


def _finish(leaf: Leaf, event: Finish) -> tuple[Leaf, tuple[Action, ...]]:
    if leaf.state is not State.TRANSIENT or event.owner not in leaf.owners:
        raise ValueError("owner must own a transient leaf to finish")
    owners = tuple(owner for owner in leaf.owners if owner != event.owner)
    target = leaf.target
    if event.ending in {Ending.ARTIST, Ending.PLAIN}:
        target = (event.ending, event.target)
    if owners:
        return replace(leaf, owners=owners, target=target), ()
    if event.remover:
        state, action = State.REMOVED, Action(Kind.FREEZE)
    elif not leaf.cancelled and target is not None:
        ending, ref = target
        if ending is Ending.ARTIST:
            state, action = State.ATTACHED, Action(Kind.ADOPT, ref)
        else:
            state, action = State.SHAPED, Action(Kind.SHAPE_FROM_TARGET, ref)
    elif event.ending is Ending.START:
        state = leaf.origin if leaf.origin is not None else State.ATTACHED
        action = Action(
            {
                State.ATTACHED: Kind.REBUILD,
                State.SHAPED: Kind.USE_SHAPE,
                State.REMOVED: Kind.FREEZE,
            }[state]
        )
    else:
        state, action = State.SHAPED, Action(Kind.SHAPE_FROM_BUFFER)
    result = Leaf(state)
    actions: tuple[Action, ...] = (action,)
    for deferred in leaf.deferred:
        result, extra = transition(result, deferred)
        actions += extra
    return result, actions


def transition(leaf: Leaf, event: Event) -> tuple[Leaf, tuple[Action, ...]]:
    """Apply one lifecycle event without mutating the input leaf.

    Parameters
    ----------
    leaf
        Current immutable state, owners and deferred events.
    event
        Event attributed by the Manim layer.

    Returns
    -------
    tuple of Leaf and tuple of Action
        Updated leaf and actions in execution order.

    Raises
    ------
    ValueError
        If an owner begins twice or finishes without owning a transient leaf.
    TypeError
        If the event type is unknown.
    """
    state = leaf.state
    if isinstance(event, Read):
        kind = {
            State.ATTACHED: Kind.REBUILD_IF_DIRTY,
            State.TRANSIENT: Kind.READ_BUFFER,
            State.REMOVED: Kind.READ_BUFFER,
            State.SHAPED: Kind.READ_SHAPE,
        }[state]
    elif isinstance(event, (DataChange, Refresh, Rebind)):
        if state is State.TRANSIENT:
            return replace(leaf, deferred=(*leaf.deferred, event)), ()
        if isinstance(event, DataChange):
            kind = Kind.MARK_DIRTY if state is State.ATTACHED else Kind.IGNORE
        elif isinstance(event, Refresh):
            if state is State.ATTACHED:
                kind = Kind.REBUILD
            else:
                return replace(leaf, state=State.ATTACHED), (Action(Kind.REATTACH),)
        else:
            return leaf, (
                () if state is State.REMOVED else (Action(Kind.REBIND, event.system),)
            )
    elif isinstance(event, Write):
        if state in {State.TRANSIENT, State.REMOVED}:
            kind = Kind.WRITE_BUFFER
        elif event.writer is Writer.FRAME:
            kind = Kind.IGNORE
        elif event.writer is Writer.BARE:
            kind = Kind.KEEP_UNTIL_REBUILD
        else:
            kind = (
                Kind.OWN_TRANSFORM if state is State.ATTACHED else Kind.TRANSFORM_SHAPE
            )
    elif isinstance(event, ReversePoints):
        kind = {
            State.ATTACHED: Kind.TOGGLE_DIRECTION,
            State.TRANSIENT: Kind.WRITE_BUFFER,
            State.REMOVED: Kind.REVERSE_BUFFER,
            State.SHAPED: Kind.REVERSE_SHAPE,
        }[state]
    elif isinstance(event, Begin):
        if event.owner in leaf.owners:
            raise ValueError("owner already owns this leaf")
        if state is State.TRANSIENT:
            return replace(leaf, owners=(*leaf.owners, event.owner)), ()
        reattach = event.introducer and state in {State.REMOVED, State.SHAPED}
        origin = State.ATTACHED if reattach else state
        actions = (Action(Kind.REATTACH), Action(Kind.RETAKE_START)) if reattach else ()
        return Leaf(State.TRANSIENT, (event.owner,), origin), actions
    elif isinstance(event, Finish):
        return _finish(leaf, event)
    elif isinstance(event, Become):
        if event.artist:
            if state is State.TRANSIENT:
                return replace(
                    leaf, origin=State.ATTACHED, cancelled=True, target=None
                ), (
                    Action(Kind.ADOPT, event.other),
                    Action(Kind.CANCEL_TARGETS),
                )
            return replace(leaf, state=State.ATTACHED), (
                Action(Kind.ADOPT, event.other),
            )
        action = Action(Kind.SHAPE_FROM_TARGET, event.other)
        if state is State.TRANSIENT:
            return replace(leaf, origin=State.SHAPED), (action,)
        return replace(leaf, state=State.SHAPED), (action,)
    elif isinstance(event, Copy):
        kind = {
            State.ATTACHED: Kind.COPY_ATTACHED,
            State.TRANSIENT: Kind.COPY_REBUILT,
            State.REMOVED: Kind.COPY_REMOVED,
            State.SHAPED: Kind.COPY_SHAPED,
        }[state]
    elif isinstance(event, SuspendUpdating):
        return leaf, ((Action(Kind.PAUSE_UPDATERS),) if state is State.ATTACHED else ())
    elif isinstance(event, FrameMoved):
        if state is State.REMOVED:
            return leaf, ()
        kind = Kind.COPIES_FOLLOW if state is State.TRANSIENT else Kind.FOLLOW_FRAME
    else:
        raise TypeError(f"event has unknown type {type(event).__name__}")
    return leaf, (Action(kind),)
