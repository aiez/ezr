<!-- Copyright (c) 2026 Tim Menzies, MIT License -->
# ezr2: a tour

A textbook in genetic-stanza form. Read top-to-bottom: each
concept appears in build order, atoms first, call sites last.
Numbered traces (`[1]>`) are a live `python3 -i ezr2.py`
session; outputs are verbatim.

    AUTHOR-CONFIG
    audience: Python dev, new to active learning
    assumed:  recursion, dicts, basic stats
    language: Python 3
    depth:    terse
    tone:     K&R
    prose:    65 cols   code: 4-space   repl: [1]>

The whole idea: labels (a row's distance to its goals) are
expensive. Spend few. `disty` is the only oracle; everything
else is free arithmetic over the cheap x-columns.

## Atoms: Num and Sym

A `Num` is a 3-tuple `(n, mu, m2)` — count, running mean, and
sum of squared deviations. A `Sym` is just a `dict` of value
counts. Two summaries, one numeric, one symbolic.

    Sym = dict
    def Num(n=0, mu=0, m2=0): return (n, mu, m2)

`welford` folds one value into a Num in a single pass; `sd`
reads a standard deviation back out of `m2`. No stored list.

    def welford(v, n, mu, m2):
      n += 1; d = v - mu; mu += d / n
      return (n, mu, m2 + d * (v - mu))

`adds` folds a stream into a Num. `add` dispatches on type:
Num via welford, Sym via a count bump.

    [1]> Num()
    (0, 0, 0)
    [2]> c = adds([2,4,4,4,5,5,7,9]); c
    (8, 5.0, 32.0)
    [3]> round(mu_(c),2), round(sd(c),2)
    (5.0, 2.14)

Sibling spreads: `sd` for a Num, `entropy` for a Sym. Note
`adds` can't seed a Sym — an empty dict is falsy, so
`i or Num()` discards it. Build a Sym with `add` in a loop.

    [4]> s = Sym()
         for v in "aabbbc": add(s,v)
         s
    {'a': 2, 'b': 3, 'c': 1}
    [5]> round(entropy(s),2)
    1.46

## Data: rows and roles

`Data` reads a CSV. The first row is column names; their
suffixes assign roles. `Upper` = Num, `lower` = Sym. A goal
ends `+` (maximize), `-` (minimize), or `!` (klass). `X`
skips; `~` marks a sensitive column.

    def roles(data):
      for at, s in enumerate(data.names):
        data.cols[at] = Num() if s[0].isupper() else Sym()
        if s[-1] == "X": continue
        if s[-1] in "+-!":
          data.y += [at]; data.goal[at] = s[-1] == "+"
          if s[-1] == "!": data.klass = at
        else:
          data.x += [at]
          if s[-1] == "~": data.protect += [at]
      return data

So `x` are predictors, `y` are goals. `goal[at]` is `True`
when bigger is better.

    [6]> d = Data(csv(the.file))
         len(d.rows), d.names[:3]
    (398, ['Clndrs', 'Volume', 'HpX'])
    [7]> d.x[:4]
    [0, 1, 3, 4]
    [8]> d.y, [d.names[a] for a in d.y]
    ([5, 6, 7], ['Lbs-', 'Acc+', 'Mpg+'])
    [9]> d.rows[0]
    [8, 304, 193, 70, 1, 4732, 18.5, 10]

## Distance: y-space and x-space

`disty` is the **label**: how far a row sits from the ideal
goals, 0 = best. Each goal is normalized to 0..1, compared to
its `goal` direction, then aggregated by a p-norm. The
`labelled` hook is where a real evaluator would fill the row.

    def disty(data, row, **kw):
      row = labelled(row)
      return minkowski(
        (abs(norm(data.cols[at], row[at]) - data.goal[at])
         for at in data.y if row[at] != "?"), **kw)

    [10]> round(disty(d, d.rows[0]), 3)
    0.786
    [11]> best = min(d.rows, key=lambda r: disty(d,r))
          round(disty(d,best),3), best[:5]
    (0.075, [4, 90, 48, 78, 2])

`distx` is its sibling over the x-columns — free to compute,
no goals consulted. Active learning leans on this: cluster in
x-space, spend labels sparingly in y-space.

    [12]> round(distx(d, d.rows[0], best), 3)
    0.785

## Active learning: acquire

`project` maps rows onto an east-west line through two distant
labelled poles (the y-better one is east). `acquire` then
labels `grow` rows per round, keeps the promising fraction,
and repeats until the budget (`budget-check`) is spent.

    def acquire(data):
      x   = lambda a,b: distx(data, a, b)
      y   = lambda r: disty(data, r)
      cap = the.budget - the.check
      pool = shuffle(data.rows)
      lab  = {}
      while len(lab) < cap and len(pool) >= 2*the.leaf:
        here, k = [], 0
        for r in pool:
          if id(r) in lab: here.append(r)
          elif k < the.grow and len(lab) < cap:
            lab[id(r)] = r; here.append(r); k += 1
        n = max(1, int((1-the.keepf)*len(pool)))
        pool = sorted(pool, key=project(here, x, y))[n:]
      return sorted(lab.values(), key=y)

`lab` is keyed on `id(row)` (rows are mutable lists, so
unhashable); its length *is* the budget. `wins` grades a row:
% of the gap from median to best that it closes.

    [13]> got = acquire(d)
          len(got), round(disty(d,got[0]),3)
    (42, 0.096)
    [14]> round(wins(d)(got[0]), 1)
    95.4

42 labels land within 4% of the best disty in the data —
~95% of the median-to-best gap closed.

## Trees: cuts, tree, show

A cut splits rows to minimize `impurity` (a Num's `m2`, a
Sym's entropy×count). `cuts` only yields splits leaving
`leaf` rows on **both** sides — the size guard lives here, in
the selector, so a degenerate one-row cut never wins `min`.

    def cuts(data,rows,at,Y):
      xy  = [(r[at], Y(r)) for r in rows if r[at] != "?"]
      n   = len(xy)
      tot = adds(y for _,y in xy)
      cut = lambda l,k: (impurity(l)+impurity(mix(tot,l,-1)),at,k)
      big = lambda lo: the.leaf <= lo <= n-the.leaf
      ...

`tree` recurses on the lowest-cost cut. `has` routes a row
(`?` goes yes-side); `if yes and no` guards the one case the
selector can't — a `?`-heavy column emptying a side.

    def tree(data, rows, Y=None, lvl=0):
      Y = Y or (lambda r: disty(data, r))
      t = o(at=None, mu=mu_(adds(Y(r) for r in rows)),
            n=len(rows), rows=rows)
      if len(rows) >= 2*the.leaf and lvl < the.maxd:
        if cut := min((c for at in data.x
                       for c in cuts(data,rows,at,Y)),default=0):
          _, at, v = cut
          col = data.cols[at]
          yes, no = [], []
          for r in rows:
            (yes if has(r,col,at,v) else no).append(r)
          if yes and no:
            t.at, t.v = at, v
            t.yes = tree(data, yes, Y, lvl+1)
            t.no  = tree(data, no,  Y, lvl+1)
      return t

`show` prints it: a `win` column, leaf size `n`, the goal
means, then the branch tests. `+`/`-` flag the best/worst
leaf; subtrees sort best-first.

    [15]> t = tree(d, acquire(d)); show(d, t)
      win     n    Lbs-   Acc+   Mpg+
        2    44  2515.4   16.5   28.2
       41    21  2017.8   16.9   31.9  Volume <= 108
    +  69     7  1920.4   17.8   32.9  |  Volume <= 85
       27    14  2066.4   16.4   31.4  |  Volume > 85
       ...
      -33    23  2969.7   16.1   24.8  Volume > 108
       ...
    - -89     3  3487.3   14.6   16.7  |  |  Volume > 225

Low Volume + light cars sit at the good (`+`) leaf, Mpg 32.9;
the heavy `-` leaf bottoms out at Mpg 16.7.

## The budget rig: tacquire

`acquire` searches all the data. `tacquire` is the honest
generalization test: split 50:50, **acquire on the train
half only**, build a tree on those ~45 rows, then use it to
rank the unseen test half and label the top `check`.

    def tacquire(data):
      rows  = shuffle(data.rows)
      mid   = len(rows)//2
      train, test = rows[:mid], rows[mid:]
      got   = acquire(clone(data, train))
      t     = tree(data, got)
      top   = sorted(test,
                     key=lambda r: leaf(data,t,r))[:the.check]
      return min(top, key=lambda r: disty(data,r))

`clone(data, rows)` is a fresh `Data` over the train subset,
so `acquire`'s pool is the train half. The total label cost
is one budget — no peeking at test.

    [16]> best = tacquire(Data(csv(the.file)))
          round(disty(d2,best),3), round(wins(d2)(best),1)
    (0.105, 93.3)

## Plumbing

`thing` coerces a CSV cell to int/float/bool/str. `csv`
yields rows as **lists** (so `labelled` can mutate them).
`settings` parses the module docstring's `--key ... = val`
lines into `the` — the options table *is* the config, no
duplicate defaults to drift.

    def settings(doc):
      pat = r"--(\w+)\s+[^=\n]*=\s*(\S+)"
      return o(**{k: thing(v)
                  for k,v in re.findall(pat, doc)})

    the = settings(__doc__)

`main` applies `--key=val` overrides, then runs any named
`test_*`. Tests are bare names on the command line:

    $ python3 ezr2.py acquires --budget=80
    $ python3 ezr2.py tree
    $ pytest ezr2.py

That is the whole arc: cheap x-distance to steer, expensive
y-distance to label, a tree to explain, a budget to keep
everyone honest.
