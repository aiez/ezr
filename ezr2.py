#!/usr/bin/env python3 -B
"""
ezr2: landscape analysis for xai and optimization CSV data.
(c) 2026, Tim Menzies <timm@ieee.org>, MIT license

USAGE: python3 ezr2.py [--key=val ...] [test ...]

OPTIONS: (defaults below are parsed into `the`):
  --file   data file             = ../optimiz/misc_auto93.csv
  --seed   random seed           = 1
  --leaf   tree min leaf rows    = 3
  --maxd   tree max depth        = 8
  --grow   add labels/round      = 4
  --budget labeling cap          = 50
  --cap    max rows kept         = 1024
  --check  rows labelled by tree = 5
  --keepf  keep frac             = 0.66
  --round  decimals shown        = 3
  --landscape  active | random   = active
  -h       print this help

TESTS: (run with their bare name):
  disty       rows by disty: top 5 / bottom 5
  landscape   20 shuffles; best disty per run
  landscapes  one mean-win line (the sweep)
  tree      build+show a tree on acquired rows
  holdout  50:50 split; tree picks best test row
  holdouts holdout x20; land vs random verdict
  pure     no tree: best labelled, land vs random
  same     demo+validate the same() stat test
  all      run every test above, reseting seed each
"""
"""
INSTALL: grab this script and some sample data, then run a test:
  wget -O ezr2.py     https://github.com/aiez/ezr#file-ezr2-py
  wget -O auto93.csv  https://github.com/aiez/optimiz#file-misc_auto93-csv
  python3 ezr2.py --file=auto93.csv disty

MODES: optimize a static CSV (format below), or a live model by
  overriding labelled() to compute goals on demand -- worked example
  in dtlz4.py (https://github.com/aiez/ezr#file-dtlz4-py).

DATA: comma-separated, first row names the columns. A name's last
character sets that column's role; its first sets its type:
  Upper case first letter  -> numeric  (else: symbolic)
  +  /  -   suffix         -> goal: maximize / minimize  (a y-column)
  !         suffix         -> klass   (a y-column)
  X         suffix         -> ignore this column
  ~         suffix         -> protected x-column
  (no suffix)              -> ordinary x-column (input)
E.g. the auto93 header Clndrs,Volume,HpX,Model,origin,Lbs-,Acc+,Mpg+
has numeric inputs (Clndrs/Volume/Model), a symbolic input (origin),
an ignored column (HpX), and goals minimize Lbs, maximize Acc/Mpg.

DISTY: every row's "distance to heaven" -- its distance to the ideal
point where all goals are best (0 = ideal, 1 = worst). `disty` reads
only the y-columns, so optimization can score a row without seeing
how it was made. `python3 ezr2.py disty` sorts rows by disty and
prints the best 5, a blank line, then the worst 5:

  Clndrs  Volume  HpX  Model  origin  Lbs-  Acc+  Mpg+  disty
       4      90   48     78       2  1985  21.5    40  0.075
       ...                                              ...
       8     455  225     70       1  4425    10    10  0.954

Best rows (disty~0) are light, high-Mpg cars; worst (disty~1) are
heavy guzzlers. Optimizers seek low-disty rows while labelling
(inspecting the y of) as few rows as possible.
"""
import re, sys, random
from math import log2, exp
from bisect import bisect_left, bisect_right
from types import SimpleNamespace as o
isa = isinstance
BIG = 1e32
TINY = 1e-32

#-- Cols --------------------------------------------------------
Sym = dict
def Num(n=0, mu=0, m2=0): return (n, mu, m2)

def n_(num)  : return num[0]
def mu_(num) : return num[1]
def m2_(num) : return num[2]

def welford(v, n, mu, m2):
  "Fold value v into a Num; return new (n,mu,m2)."
  n += 1; d  = v - mu; mu += d / n
  return (n, mu, m2 + d * (v - mu))

def sd(num): n,mu,m2 = num; return 0 if n<2 else (max(0,m2)/(n-1))**.5

def entropy(d):
  "Shannon entropy of a Sym (a dict of counts)."
  N = sum(d.values()) or 1
  return -sum(v/N*log2(v/N) for v in d.values() if v)

def mix(i, j, inc=1):
  "Merge two cols; inc=-1 subtracts j from i."
  if isa(i, Sym):
    return {k: i.get(k, 0) + inc * j.get(k, 0) for k in i | j}
  (ni, mui, m2i), (nj, muj, m2j) = i, j
  n = ni + inc * nj
  if n <= 0: return Num()
  d  = muj - mui
  mu = (ni * mui + inc * nj * muj) / n
  m2 = m2i + inc * m2j + inc * d * d * ni * nj / n
  return Num(n, mu, max(0, m2))      # subtraction can underflow m2 below 0

#-- Data --------------------------------------------------------
def Data(src):
  "Build a table; first row = column names."
  src  = iter(src)
  data = o(names=next(src), cols={}, x=[], y=[], goal={},
           klass=None, protect=[], rows=[])
  return adds(src, roles(data))

def clone(data, rows):
  "Fresh Data over a subset of rows."
  return Data([data.names] + rows)

def roles(data):
  "Tag cols x/y/klass/protect from name suffixes."
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

def adds(src, i=None):
  "Fold a stream of values/rows into i (Num by default)."
  i = Num() if i is None else i        # keep an empty Sym; {} is falsy
  for v in src: i = add(i,v)
  return i

def add(i,v):
  "Add one value to a col, or one row to a Data."
  if isa(i,o):
    for at,col in i.cols.items(): i.cols[at] = add(col,v[at])
    i.rows += [v]
  elif v != "?":
    if isa(i,Sym): i[v] = i.get(v,0) + 1
    else: i = welford(v, *i)
  return i

#-- Dist --------------------------------------------------------
def mid(i): return max(i,key=i.get) if isa(i,Sym) else mu_(i)
def var(i): return entropy(i)       if isa(i,Sym) else sd(i)

def norm(num, v):
  "Map v to 0..1 via a logistic on its z-score."
  if v == "?": return v
  z = (v - mu_(num)) / (sd(num) + 1e-32)
  return 1 / (1 + exp(-1.7 * max(-3, min(3, z))))

def minkowski(vals, p=2):
  "Aggregate per-item distances via the p-norm."
  tot = nn = 0
  for v in vals: tot += v**p; nn += 1
  return (tot / (nn or 1)) ** (1/p)

def gap(col, u, v):
  "Distance 0..1 between two values of one column."
  if u == v == "?": return 1
  if isa(col, Sym): return u != v
  u, v = norm(col, u), norm(col, v)
  if u == "?": u = 1 if v < .5 else 0
  if v == "?": v = 1 if u < .5 else 0
  return abs(u - v)

def labelled(row): return row

def disty(data, row, **kw):
  "Row's distance to the best goals (0 = ideal)."
  row = labelled(row)
  return minkowski(
    (abs(norm(data.cols[at], row[at]) - data.goal[at])
     for at in data.y if row[at] != "?"), **kw)

def distx(data, r1, r2, **kw):
  "Distance between two rows over the x-columns."
  return minkowski((gap(data.cols[at], r1[at], r2[at])
                    for at in data.x), **kw)

def wins(data):
  "Grader: row -> % of gap to best closed, [-100,100]."
  ys = sorted(disty(data,r) for r in data.rows)
  lo, b4 = ys[0], ys[len(ys)//2]
  return lambda r: max(-100, min(100,
    100 * (1 - (disty(data,r)-lo) / (b4-lo+TINY))))

#-- Landscape ---------------------------------------------------
def project(rows, x, y):
  "Row -> position on the east-west line (x=dist,y=goal)."
  far  = lambda r: max(rows, key=lambda z: x(z, r))
  east = far(rows[0]); west = far(east)
  if y(east) < y(west): east, west = west, east
  c = x(east, west) + TINY
  return lambda r: (x(east,r)**2 + c*c - x(west,r)**2)/(2*c)

def landscape(data):
  "Label <=budget-check rows, best first. --landscape picks how."
  y   = lambda r: disty(data, r)
  cap = the.budget - the.check
  if the.landscape == "random":
    return sorted(some(data.rows, cap), key=y)
  x   = lambda r1, r2: distx(data, r1, r2)
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

#-- Tree build --------------------------------------------------
def mid(col): return max(col,key=col.get) if isa(col,Sym) else mu_(col)
def var(col): return entropy(col)          if isa(col,Sym) else sd(col)

def size(col): return sum(col.values()) if isa(col,Sym) else n_(col)

def score(here, there):
  "Split cost (lower=better): size-weighted nean of var (sd|entropy)."
  a, b = size(here), size(there)
  return (var(here)*a + var(there)*b) / (a + b + 1e-32)

def cuts(data,rows,at,Y,accum=Num):
  "Yield (cost,at,v) splits with both sides >= the.leaf. accum=Num|Sym"
  xy  = [(r[at], Y(r)) for r in rows if r[at] != "?"]
  n   = len(xy)
  tot = adds((y for _,y in xy), accum())
  cut = lambda here,k: (score(here, mix(tot,here,-1)), at,k)
  big = lambda lo: the.leaf <= lo <= n-the.leaf
  if isa(data.cols[at], Sym):
    for k in {x for x,_ in xy}:
      ys = [y for x,y in xy if x==k]
      if big(len(ys)): yield cut(adds(ys, accum()), k)
  else:
    xy.sort(); me=accum()
    for j,(x,y) in enumerate(xy):
      me = add(me, y)
      if j+1 < n and x != xy[j+1][0] and big(j+1):
        yield cut(me, x)

def has(row, col, at, v):
  "Does row fall on the yes-side of a cut? (? = yes)."
  w = row[at]
  return w == "?" or (v == w if isa(col, Sym) else w <= v)

def tree(data, rows, Y=None, accum=Num, lvl=0):
  "Recursively split rows on the min-cost cut. accum=Num|Sym."
  Y = Y or (lambda r: disty(data, r))
  t = o(at=None, mid=mid(adds((Y(r) for r in rows), accum())),
        n=len(rows), rows=rows)
  if len(rows) >= 2*the.leaf and lvl < the.maxd:
    if cut := min((c for at in data.x
                   for c in cuts(data,rows,at,Y,accum)), default=0):
      _, at, v = cut
      col = data.cols[at]
      yes, no = [], []
      for r in rows: (yes if has(r,col,at,v) else no).append(r)
      if yes and no:
        t.at, t.v = at, v
        t.yes = tree(data, yes, Y, accum, lvl+1)
        t.no  = tree(data, no,  Y, accum, lvl+1)
  return t

def leaf(data, t, row):
  "Walk a row down to its leaf; return the leaf's mid."
  while t.at is not None:
    t = t.yes if has(row,data.cols[t.at],t.at,t.v) else t.no
  return t.mid

#-- Tree show ---------------------------------------------------
def leaves(t):
  "Yield every leaf node of a tree."
  if t.at is None: yield t
  else: yield from leaves(t.yes); yield from leaves(t.no)

def show(data, t):
  "Pretty-print a tree: win, n, goal means, then branches."
  y  = lambda r: disty(data, r)
  vs = sorted(y(r) for r in t.rows)
  blo, bmd = vs[0], vs[len(vs)//2]
  win= lambda rows: int(100*(1 - (
        sum(y(r) for r in rows)/len(rows) - blo)/(bmd-blo+TINY)))
  ws = [win(x.rows) for x in leaves(t)]
  lo, hi = min(ws), max(ws)
  rnd  = lambda v: round(v, the.round) if isa(v, float) else v
  cond = lambda t,b: "%s %s %s" % (data.names[t.at],
    ("==" if b else "!=") if isa(data.cols[t.at],Sym)
    else ("<=" if b else ">"), rnd(t.v))
  best, worst = chr(0x25B2), chr(0x25BC)        # up/down triangles
  head = " ".join("%8s" % data.names[a] for a in data.y)
  print("%s %4s %5s  %s" % (" ", "win", "n", head))
  def go(t, pad="", edge=""):
    w = win(t.rows)
    m = " "
    if t.at is None: m = best if w==hi else worst if w==lo else " "
    mids = " ".join("%8.*f" % (the.round, mid(adds(r[a] for r in t.rows)))
                    for a in data.y)
    print(("%s %4d %5d  %s  %s%s"
           % (m, w, t.n, mids, pad, edge)).rstrip())
    if t.at is not None:
      p2 = pad + ("|  " if edge else "")
      kids = [(t.yes, cond(t,True)), (t.no, cond(t,False))]
      for kid,e in sorted(kids, key=lambda ke: ke[0].mid):
        go(kid, p2, e)
  go(t)

#-- misc --------------------------------------------------------
def shuffle(lst): return random.sample(lst, len(lst))
def some(lst, k): return random.sample(lst, min(k, len(lst)))

def cliffs(xs, ys):
  "Cliff's delta effect size in 0..1 (0 = identical)."
  ys = sorted(ys); m = len(ys)
  gt = sum(bisect_left(ys, x)      for x in xs)
  lt = sum(m - bisect_right(ys, x) for x in xs)
  return abs(gt - lt) / (len(xs) * m + 1e-32)

def ks(xs, ys):
  "Kolmogorov-Smirnov: max gap between the two CDFs."
  xs, ys = sorted(xs), sorted(ys); n, m = len(xs), len(ys)
  gap = lambda v: abs(bisect_right(xs,v)/n
                      - bisect_right(ys,v)/m)
  return max(map(gap, xs + ys))

def cohen(xs, ys, eps=0.35):
  "Small effect: |mean gap| < eps * pooled stdev."
  x, y = adds(xs), adds(ys); n, m = n_(x), n_(y)
  pooled = (((n-1)*sd(x)**2 + (m-1)*sd(y)**2)/(n+m-2))**.5
  return abs(mu_(x) - mu_(y)) <= eps * (pooled + TINY)

def same(xs, ys, cliff=0.195, conf=1.36):
  "True if xs,ys are statistically indistinguishable."
  if not cohen(xs, ys): return False
  if cliffs(xs, ys) > cliff: return False
  n, m = len(xs), len(ys)
  return ks(xs, ys) <= conf * ((n + m) / (n * m)) ** 0.5

def thing(s):
  "Coerce a string to int/float/bool, else leave as str."
  if (s[1:] if s[:1]=="-" else s).isdigit(): return int(s)
  try: return float(s)
  except ValueError: return s=="True" or (s!="False" and s)

def settings(doc):
  "Parse '--key ... = val' lines of doc into an o()."
  pat = r"--(\w+)\s+[^=\n]*=\s*(\S+)"
  return o(**{k: thing(v) for k,v in re.findall(pat, doc)})

def csv(file, clean=lambda s: s.partition("#")[0].split(",")):
  "Yield typed rows (lists) from a CSV file."
  with open(file, encoding="utf-8") as f:
    for line in f:
      row = [x.strip() for x in clean(line)]
      if any(row): yield [thing(x) for x in row]

#-- Tests (test_*) ----------------------------------------------
def test_disty():
  "Rows sorted by disty: header, top 5, blank, bottom 5."
  data = Data(csv(the.file))
  rows = sorted(data.rows, key=lambda r: disty(data, r))
  hdr  = list(data.names) + ["disty"]
  fmt  = lambda r: [str(v) for v in r]+["%.3f" % disty(data,r)]
  body = [fmt(r) for r in rows[:5] + rows[-5:]]
  w = [max(len(row[c]) for row in [hdr]+body)
       for c in range(len(hdr))]
  line = lambda cs: print("  ".join(c.rjust(w[i])
                                    for i,c in enumerate(cs)))
  line(hdr)
  for r in body[:5]: line(r)
  print()
  for r in body[5:]: line(r)

def test_landscape():
  "20 shuffles; per run, best found by active landscape vs random pick."
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  W, rows_out = wins(data), []
  for i in range(20):
    random.seed(the.seed + i); data.rows = shuffle(data.rows)
    the.landscape = "active"; a = landscape(data)[0]
    the.landscape = "random"; r = landscape(data)[0]
    rows_out += [(disty(data,a), W(a), disty(data,r), W(r))]
  the.landscape = "active"
  up = chr(0x25B2)          # marks whichever side won (lower disty) this run
  print("rank  aDisty  aWin   rDisty  rWin  win  (%s)" % the.file.split("/")[-1])
  for k,(ad,aw,rd,rw) in enumerate(sorted(rows_out)):
    win = "tie" if ad==rd else ("%s active" % up if ad<rd else "%s random" % up)
    print("%4d %7.3f %5.1f  %7.3f %5.1f  %s" % (k, ad, aw, rd, rw, win))
  assert sum(ad for ad,_,_,_ in rows_out)/len(rows_out) < 0.3

def test_landscapes():
  "One summary line: mean win/disty over 20 runs."
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  W, ds, ws, n = wins(data), [], [], 0
  for i in range(20):
    random.seed(the.seed + i)
    data.rows = shuffle(data.rows)
    got = landscape(data)
    ds += [disty(data,got[0])]; ws += [W(got[0])]; n = len(got)
  print("%6.1f %7.3f %4d  %s" % (sum(ws)/len(ws),
        sum(ds)/len(ds), n, the.file.split("/")[-1]))

def test_tree():
  "Build a tree over landscape's rows and print it."
  random.seed(the.seed)
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  show(data, tree(data, landscape(data)))

def test_trees():
  "Same budget: random-trained vs landscape-trained tree."
  random.seed(the.seed)
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  land = landscape(data)
  rand = some(data.rows, len(land))
  W = wins(data)
  for tag, rows in [("random", rand), ("landscape", land)]:
    best = min(rows, key=lambda r: disty(data,r))
    print("\n== %s  n=%d  best disty=%.3f  win=%.1f ==" %
          (tag, len(rows), disty(data,best), W(best)))
    show(data, tree(data, rows))

def holdout(data):
  "Budget rig: landscape train -> tree -> pick from test."
  rows  = shuffle(data.rows)
  mid   = len(rows)//2
  train, test = rows[:mid], rows[mid:]
  got   = landscape(clone(data, train))
  t     = tree(data, got)
  top   = sorted(test, key=lambda r: leaf(data,t,r))[:the.check]
  return min(top, key=lambda r: disty(data,r))

def vs(data, pick):
  "active vs random over 20 runs of pick(); stat verdict line."
  W, out = wins(data), {}
  for mode in ("active", "random"):
    the.landscape = mode; out[mode] = []
    for i in range(20):
      random.seed(the.seed + i); out[mode] += [W(pick(data))]
  the.landscape = "active"
  L, R = out["active"], out["random"]
  ml, mr = sum(L)/20, sum(R)/20
  v = "tie" if same(L, R) else ("land" if ml > mr else "rand")
  print("%6.1f %6.1f %-5s %s" % (ml, mr, v,
        the.file.split("/")[-1]))

def test_holdout():
  "One run: the holdout-picked best row's disty and win."
  random.seed(the.seed)
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  b = holdout(data)
  print("best disty %.3f  win %.1f  (%s)" % (disty(data,b),
        wins(data)(b), the.file.split("/")[-1]))

def test_holdouts():
  "active vs random landscape, through the holdout pipeline."
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  vs(data, holdout)

def test_pure():
  "active vs random landscape; best labelled row, no tree."
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  vs(data, lambda d: landscape(d)[0])

def test_same():
  "Validate same(): small shift = same, big shift = differ."
  random.seed(the.seed)
  a = [random.gauss(0, 1) for _ in range(20)]
  shift = lambda d: [x + d for x in a]
  print("shift  same   cliffs cohen")
  for d in (0, 0.1, 0.3, 0.5, 1.0, 2.0):
    b = shift(d)
    print(" %+.1f  %-5s  %.2f   %s" % (d, same(a,b),
          cliffs(a,b), cohen(a,b)))
  assert same(a, a) and not same(a, shift(2))

def test_all():
  "Run every other test_*, reseting the seed before each."
  for n,f in list(globals().items()):
    if n.startswith("test_") and n != "test_all":
      print("\n#", n, "-"*40)
      try: random.seed(the.seed); f()
      except Exception as e: print("FAIL:", n, type(e).__name__, e)

#-- Main --------------------------------------------------------
def main(funs):
  "Apply --key=val to `the`, then run each named test_*."
  if "-h" in sys.argv: return print(__doc__)
  for a in sys.argv[1:]:
    if a[:2]=="--" and "=" in a:
      k,v = a[2:].split("=",1)
      if k in vars(the): setattr(the, k, thing(v))
  for a in sys.argv[1:]:
    if (n := "test_"+a) in funs:
      random.seed(the.seed); funs[n]()

the = settings(__doc__)
if __name__ == "__main__": main(globals())
