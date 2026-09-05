# API sketch — for review

Draft public surface implied by decisions D1-D10 in `docs/grill-log.md`. Nothing here
is implemented or locked. Names are placeholders; semantics are not.

Leave comments inline, anywhere, in any language. Open questions are marked `Q:` and
have an `A:` line to fill in.

---

## 1. Construction

```python
from manim_plots import CartesianAxes

ax = CartesianAxes(
    x=(0, 10),
    y=(-1, 1),
    scale={"x": "log"},  # linear | log | symlog
)
```

Q1.1 — Class name. `CartesianAxes` avoids shadowing Manim's `Axes` on a
`from manim import *`. Alternatives: `Cartesian`, `Plot`, `Axes2D`.
A1.1:  or from manim_plots import *

Q1.2 — Range keywords. `x=(0, 10)` vs Manim's `x_range=[0, 10, 1]`. The third element
in Manim's triple is a step, which in our model belongs to the locator, not the range.
A1.2: we also should be able to specify the length of each axis. The API shold be 
really simmilar to the current manim one. 

Q1.3 — Should the constructor take a `scale=` dict, or per-axis keywords
(`x_scale="log"`)?
A1.3: It would be great if user can define his own scale
by providing forword and backword transforming functions

---

## 2. Artists

```python
curve = ax.plot(lambda t: np.sin(t))  # analytic source, adaptive sampling
line = ax.line(xs, ys)  # array source
pts = ax.scatter(data)  # [(x, y), ...] or (xs, ys)
```

Standalone and rebindable (D2, D3):

```python
free = Scatter(xs, ys)  # unattached: renders in the identity system (scene space)
free.attach(ax)  # binds data AND parents into the axes' data layer
free.detach()  # reverses both
```

Q2.1 — **The open fork.** One overloaded verb or separate verbs?

- (A) `ax.plot(f)` and `ax.plot(xs, ys)` — one verb, matplotlib muscle memory, ugly
  typing overloads, vague errors on misuse.
- (B) `ax.plot(f)` / `ax.line(xs, ys)` / `ax.scatter(...)` — clean typing, clear
  errors, and the name says which pipeline head you get.

The difference is visible on screen, not just in the implementation: under
`ax.animate.set_range(...)` an analytic source *resamples* and draws new curve, an
array source only *reveals* what is already there (D5).

Recommendation: B.
A2.1: okay, howether I do npt particullarly like a part: `free.attach(ax)` 
it should be anotherway around. We are adding plot into the axes. 

Q2.2 — Do the axes methods (`ax.plot`) exist at all, or is construction always
`FunctionPlot(f).attach(ax)`? The methods are sugar; keeping both means two ways to do
one thing.
A2.2: yes, I think we should support creating almost any type of the plot via `.plot` method. 
The reason is simple, uesr who knows manim it expetcs such a behaviour. 
Encoruaging to different usage is an another thing

---

## 3. Axis decoration (D7 — decoration, not the mapping)

```python
ax.x.set_locator(MaxN(5))
ax.x.set_formatter(SI(unit="s"))

ax.x.ticks.direction = OUT  # IN | OUT | BOTH
ax.x.ticks.minor.count = 4
ax.x.position = "origin"  # "origin" | "bottom" | "top" | a data value
ax.x.mirror = True  # gnuplot's `set xtics mirror`

ax.x.line  # the axis line
ax.x.ticks.major  # the tick lines
ax.x.labels  # the tick labels
ax.x.grid
ax.x.labels.at(2.0).set_color(RED)  # keyed identity, survives rebuild (D10)
```

Q3.1 — `ax.x` / `ax.y`, or `ax.axes["x"]`, or `ax.x_axis` (Manim's name)?
A3.1: `ax.x` is better and ax.x_axis. Those two things should be equaivalent, 
It is just a simple getter and @property decorator

Q3.2 — Are `direction`, `position`, `mirror` plain attributes, or setters
(`set_direction(...)`)? Plain attributes read better but need `__setattr__` to mark the
node dirty (D8).
A3.2: the `__setattr__` is better, more pythonic and natural

Q3.3 — Explicit tick lists, gnuplot style:
`ax.x.set_ticks([(0, "start"), (5, r"\pi"), (10, "end")])`. Right shape?
A3.3: yes, however we can overide this functionality and allow user to pass a generator funciton.
The logic is simple, if you want a specific set of labels, and you are doing something complicated you 
would probably write a function to do it for you -> it sould accept the function and flag for 
regeneratio after some trigger with preserving modifiers if applicable

---

## 4. Data channel and animation (D8)

```python
ax.set_range(x=(0, 20))  # jumps
self.play(ax.animate.set_range(x=(0, 20)))  # interpolates the arguments, rebuilds

ax.bind(x_range=tracker)  # bind a parameter to a tracker
ax.param("x_range")  # get the tracker object back
ax.param("x_range").set_value((0, 30))  # write through the tracker

self.play(Morph(curve, other_curve))  # resample, then interpolate
```

Q4.1 — `bind(...)` / `param(...)` naming. Alternatives: `ax.tracker("x_range")`,
`ax.x.range_tracker`.
A4.1: can we use some more advanced programming, like `__getitem__` or something simmilar to make it 
`ax.x_range@(0,30,1)` or something simmilar? (do not forget about the step)

Q4.2 — Should *every* parameter be reachable by name (a string registry), or only a
documented set with dedicated accessors? A registry is uniform and introspectable; the
accessors are typed and discoverable in an IDE. 
A4.2: Answerd in previous question, howvether we want to support an intelisens as much us it is possible

---

## 5. Legend

```python
legend = Legend(curve, line)  # standalone mobject
# or
legend = ax.legend()  # collects the axes' attached artists
```

Q5.1 — Which one? Same logic as Q2.2: the free function is explicit and works across
several coordinate systems; the method is convenient and only works for one. Note that
after D3 the axes *do* know their artists, so `ax.legend()` is now cheap.
A5.1: `legend = ax.legend()` 
(maybe, in case of multiple axes we should add possiblity of joyning and separating two legengs)

Q5.2 — Where does a label come from — `ax.plot(f, label="sin")`, or
`curve.set_label("sin")`, or both?
A5.2: both, but preferable is the first option

---

## 6. Scene integration (D3)

```python
self.add(ax)  # attached artists come along; do NOT also add them
self.play(Create(curve))  # still an ordinary mobject
self.play(ax.animate.shift(RIGHT))  # geometric channel: only T changes (D4)
```

Q6.1 — Should adding an attached artist directly to the scene warn, be silently
ignored, or be allowed?
A6.1: adding an axes should NOT influance the adding curves. 

---

## 7. Anything missing

Free space. Requirements that have no home in the sketch above go here.
We didn't cover any aniamtion things in terms of writing our own animations for some common aniamtions
