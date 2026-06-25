#!/usr/bin/env python3 -B
"""
ezr2: XAI, optimization, active learning, rules, trees over CSV data.
(c) 2026, Tim Menzies <timm@ieee.org>, MIT license

USAGE: python3 ezr2.py [--key=val ...] [test ...]

OPTIONS: (defaults below are parsed into `the`):
  --file   data file            = ../optimiz/misc_auto93.csv
  --seed   random seed          = 1
  --bins   tree cut bins        = 16
  --leaf   tree min leaf rows   = 3
  --maxd   tree max depth       = 8
  --grow   acquire labels/round = 4
  --budget acquire label cap    = 50
  --cap    max rows kept        = 1024
  --check  rows labelled by tree = 5
  --keepf  acquire keep frac    = 0.66
  -h       print this help

TESTS: (run with their bare name):
  acquire  20 shuffles; report best disty found
  acquires one mean-win line (used in the sweep)
  tree     build+show a tree over --budget random rows
  tacquire 50:50 split; tree on train picks best test row
  tacquires tacquire x20; mean win/disty line
"""
import re, sys, random
from math import log2, exp
from types import SimpleNamespace as o   # o(a=1).a == 1
isa = isinstance
BIG = 1e32
TINY = 1e-32

def thing(s):                         # str -> int/float/bool/str
  if (s[1:] if s[:1]=="-" else s).isdigit(): return int(s)
  try: return float(s)
  except ValueError: return s=="True" or (s!="False" and s)

def settings(doc):                    # "--key ... = val" -> o(key=val)
  return o(**{k: thing(v)
              for k,v in re.findall(r"--(\w+)\s+[^=\n]*=\s*(\S+)", doc)})

the = settings(__doc__)

#-- Cols --------------------------------------------------------
Sym = dict
def Num(n=0, mu=0, m2=0): return (n, mu, m2)

def n_(num)  : return num[0]
def mu_(num) : return num[1]
def m2_(num) : return num[2]

def welford(v, n, mu, m2):
  n += 1; d  = v - mu; mu += d / n
  return (n, mu, m2 + d * (v - mu))

def entropy(d):                      
  N = sum(d.values()) or 1
  return -sum(v/N*log2(v/N) for v in d.values() if v)

def mix(i, j, inc=1):
  if isa(i, Sym):
    return {k: i.get(k, 0) + inc * j.get(k, 0) for k in i | j}
  (ni, mui, m2i), (nj, muj, m2j) = i, j
  n = ni + inc * nj
  if n <= 0: return Num()
  d  = muj - mui
  mu = (ni * mui + inc * nj * muj) / n
  m2 = m2i + inc * m2j + inc * d * d * ni * nj / n
  return Num(n, mu, m2)

#-- Data -------------------------------------------------------
def Data(src):
  src  = iter(src)
  data = o(names=next(src), cols={}, x=[], y=[], goal={},
           klass=None, protect=[], rows=[])
  return adds(src, roles(data))

def roles(data):
  for at, s in enumerate(data.names):
    data.cols[at] = Num() if s[0].isupper() else Sym()
    if s[-1] == "X": continue
    if s[-1] in "+-!":
      data.y += [at]; data.goal[at] = s[-1] == "+"   # +max -min
      if s[-1] == "!": data.klass = at
    else:
      data.x += [at]                       # predictor...
      if s[-1] == "~": data.protect += [at]   # ...also sensitive
  return data

def adds(src, i=None):
  i = i or Num()
  for v in src: i = add(i,v)
  return i

def add(i,v):
  if isa(i,o):
    for at,col in i.cols.items(): i.cols[at] = add(col,v[at]) 
    i.rows += [v]
  elif v != "?":
    if isa(i,Sym): i[v] = i.get(v,0) + 1
    else: i = welford(v, *i)
  return i

#-- Dist --------------------------------------------------------
def sd(num): n,mu,m2 = num; return 0 if n<2 else (m2/(n-1))**.5

def norm(num, v):                     # v -> 0..1 logistic z
  if v == "?": return v
  z = (v - mu_(num)) / (sd(num) + 1e-32)
  return 1 / (1 + exp(-1.7 * max(-3, min(3, z))))

def minkowski(vals, p=2):             # p-norm of per-item dists
  tot = nn = 0
  for v in vals: tot += v**p; nn += 1
  return (tot / (nn or 1)) ** (1/p)

def gap(col, u, v):                   # 0..1 dist of two values
  if u == v == "?": return 1
  if isa(col, Sym): return u != v
  u, v = norm(col, u), norm(col, v)
  if u == "?": u = 1 if v < .5 else 0
  if v == "?": v = 1 if u < .5 else 0
  return abs(u - v)

def disty(data, row, **kw):           # row -> goals, 0=best
  return minkowski(
    (abs(norm(data.cols[at], row[at]) - data.goal[at])
     for at in data.y if row[at] != "?"), **kw)

def memo(fn):                         # memoed fn + its cache dict.
  cache = {}                          # HOOK external evals in fn
  def f(r):
    if r not in cache: cache[r] = fn(r)
    return cache[r]
  return f, cache

def distx(data, r1, r2, **kw):        # row<->row over x-cols
  return minkowski((gap(data.cols[at], r1[at], r2[at])
                    for at in data.x), **kw)

def wins(data):                       # -> fn(rows) % gap to best
  ys = sorted(disty(data,r) for r in data.rows)
  lo, b4 = ys[0], ys[ len(ys)//2 ]
  return lambda r: \
            100 * (1 - (disty(data,r) -lo) / (b4 - lo + 1e-32))

#-- Landscape ---------------------------------------------------
def shuffle(lst): return random.sample(lst, len(lst))
def some(lst, k): return random.sample(lst, min(k, len(lst)))

def project(rows, x, y):              # row -> east-west pos (x=dist, y=goal)
  far  = lambda r: max(rows, key=lambda z: x(z, r))
  east = far(rows[0]); west = far(east)
  if y(east) < y(west): east, west = west, east
  c = x(east, west) + TINY
  return lambda r: (x(east,r)**2 + c*c - x(west,r)**2) / (2*c)

def acquire(data):                  # active-learn; spend <= budget-check
  y, ys = memo(lambda r: disty(data, r))   # local cache, dies on return
  x   = lambda r1, r2: distx(data, r1, r2)  # x-space dist (y is disty)
  cap = the.budget - the.check        # reserve check for the exploit
  pool = shuffle(data.rows)
  while len(ys) < cap and len(pool) >= 2*the.leaf:
    lab, k = [], 0
    for r in pool:
      if r in ys: lab.append(r)
      elif k < the.grow and len(ys) < cap:
        y(r); lab.append(r); k += 1   # only labelled rows orient
    n = max(1, int((1-the.keepf)*len(pool)))
    pool = sorted(pool, key=project(lab, x, y))[n:]
  return sorted(ys, key=y), y         # labelled rows + memo (reuse below)

#-- Tree build --------------------------------------------------
def impurity(col):                        
  if not isa(col, Sym): return m2_(col)
  return entropy(col) * sum(col.values()) 

def cuts(data,rows,at,Y):
  xy  = [(r[at], Y(r)) for r in rows if r[at] != "?"]
  tot = adds(y for _,y in xy)
  cut = lambda l,k: (impurity(l) + impurity(mix(tot,l,-1)), at,k)
  if isa(data.cols[at], Sym):
    for k in {x for x,_ in xy}:
      yield cut(adds(y for x,y in xy if x==k), k)
  else:
    xy.sort(); n=len(xy); l=Num()
    for j,(x,y) in enumerate(xy):
      l = add(l, y)
      if j+1 < n and x != xy[j+1][0] \
         and j*the.bins//n != (j+1)*the.bins//n:
        yield cut(l, x)     

def has(row, col, at, v):  
  w = row[at]
  return w == "?" or (v == w if isa(col, Sym) else w <= v)

def tree(data, rows, Y, lvl=0):       # Y = a memo from acquire()
  t   = o(at=None, mu=mu_(adds(Y(r) for r in rows)), 
          n=len(rows), rows=rows)
  if len(rows) >= 2*the.leaf and lvl < the.maxd:
    if cut := min((c for at in data.x 
                     for c in cuts(data,rows,at,Y)),default=0):
      _, at, v = cut
      col  = data.cols[at]
      yes, no = [], []
      for r in rows: (yes if has(r,col,at,v) else no).append(r)
      if len(yes) >= the.leaf and len(no) >= the.leaf:
        t.at, t.v = at, v
        t.yes = tree(data, yes, Y, lvl+1)
        t.no  = tree(data, no,  Y, lvl+1)
  return t

def leaf(data, t, row):               # walk to a leaf, return mu
  while t.at is not None:
    t = t.yes if has(row, data.cols[t.at], t.at, t.v) else t.no
  return t.mu

#-- Tree show ---------------------------------------------------
def show(data, t, y):                 # pretty-print; y = acquire's memo
  vs = sorted(y(r) for r in t.rows)         # cached: no new evals
  blo, bmd = vs[0], vs[len(vs)//2]          # baseline lo, median
  win= lambda rows: int(100*(1 - (
        sum(y(r) for r in rows)/len(rows) - blo)/(bmd-blo+TINY)))
  ws = [win(x.rows) for x in leaves(t)]; lo,hi = min(ws),max(ws)
  cond = lambda t,b: "%s %s %s" % (data.names[t.at],
    ("==" if b else "!=") if isa(data.cols[t.at],Sym)
    else ("<=" if b else ">"), t.v)
  head = " ".join("%6s" % data.names[a] for a in data.y)
  print(" %4s %5s  %s" % ("win", "n", head))
  def go(t, pad="", edge=""):
    w = win(t.rows)
    m = " "
    if t.at is None: m = "+" if w==hi else "-" if w==lo else " "
    mu = " ".join("%6.1f" % mu_(adds(r[a] for r in t.rows))
                  for a in data.y)
    print(("%s%4d %5d  %s  %s%s" % (m, w, t.n, mu, pad, edge)).rstrip())
    if t.at is not None:
      p2 = pad + ("|  " if edge else "")   # root adds no bar
      kids = [(t.yes, cond(t,True)), (t.no, cond(t,False))]
      for kid,e in sorted(kids, key=lambda ke: ke[0].mu):  # best 1st
        go(kid, p2, e)
  go(t)

def leaves(t):
  if t.at is None: yield t
  else: yield from leaves(t.yes); yield from leaves(t.no)

#-- IO ----------------------------------------------------------
def csv(file, clean=lambda s: s.partition("#")[0].split(",")):
  with open(file, encoding="utf-8") as f:
    for line in f:
      row = [x.strip() for x in clean(line)]
      if any(row): yield tuple(thing(x) for x in row)

#-- Tests (test_*) ----------------------------------------------
def test_acquire():                   # 20 shuffles, best disty found
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  W    = wins(data)                   # row -> % gap to best
  bests = []
  for i in range(20):
    random.seed(the.seed + i)
    data.rows = shuffle(data.rows)
    got, y = acquire(data)            # rows sorted by disty, + memo
    bests += [(y(got[0]), W(got[0]), len(got))]
  print("rank  disty    win   n  (%s)" % the.file.split("/")[-1])
  for r,(b,w,n) in enumerate(sorted(bests)):     # in disty order
    print("%4d %7.3f %6.1f %3d" % (r, b, w, n))
  assert sum(b for b,_,_ in bests)/len(bests) < 0.3

def test_acquires():                  # one summary line: mean over runs
  data = Data(csv(the.file))
  data.rows = some(data.rows, the.cap)
  W    = wins(data)
  ds, ws, n = [], [], 0
  for i in range(20):
    random.seed(the.seed + i)
    data.rows = shuffle(data.rows)
    got, y = acquire(data)
    ds += [y(got[0])]; ws += [W(got[0])]; n = len(got)
  print("%6.1f %7.3f %4d  %s" % (sum(ws)/len(ws), sum(ds)/len(ds),
        n, the.file.split("/")[-1]))

def test_tree():                      # tree over acquire's labelled rows
  random.seed(the.seed)
  data = Data(csv(the.file)); data.rows = some(data.rows, the.cap)
  rows, y = acquire(data)
  show(data, tree(data, rows, y), y)

def tacquire(data):                   # tree surrogate -> label top check
  y, ys = memo(lambda r: disty(data, r))   # local memo
  rows  = shuffle(data.rows)
  mid   = len(rows)//2
  train = some(rows[:mid], the.cap)   # at most cap rows from train
  test  = rows[mid:]
  t     = tree(data, train, y)        # surrogate; labels train (paid)
  top   = sorted(test, key=lambda r: leaf(data,t,r))[:the.check]
  for r in top: y(r)                  # spend the check labels
  return min(top, key=y), y           # best of labelled, + memo

def test_tacquire():                  # one run: show the picked best
  random.seed(the.seed)
  data = Data(csv(the.file)); data.rows = some(data.rows, the.cap)
  best, y = tacquire(data)
  print("best disty %.3f  win %.1f  (%s)" % (
        y(best), wins(data)(best), the.file.split("/")[-1]))

def test_tacquires():                 # x20 shuffles -> mean win/disty
  data = Data(csv(the.file)); data.rows = some(data.rows, the.cap)
  W = wins(data); ds, ws = [], []
  for i in range(20):
    random.seed(the.seed + i)
    best, y = tacquire(data)
    ds += [y(best)]; ws += [W(best)]
  print("%6.1f %7.3f  %s" % (sum(ws)/20, sum(ds)/20,
        the.file.split("/")[-1]))

#-- Main --------------------------------------------------------
def main(funs):                       # --key=val -> the ; run test_<x>
  if "-h" in sys.argv: return print(__doc__)
  for a in sys.argv[1:]:
    if a[:2]=="--" and "=" in a:
      k,v = a[2:].split("=",1)
      if k in vars(the): setattr(the, k, thing(v))
  for a in sys.argv[1:]:
    if (n := "test_"+a) in funs:
      random.seed(the.seed); funs[n]()   # reseed before each test

if __name__ == "__main__": main(globals())
