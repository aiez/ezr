#!/usr/bin/env python3 -B
"""cli.py: ezr command-line. One test_<name> per concept; each both
demonstrates (prints) and checks (asserts).

Usage:
  ezr [--key=val ...] --<name> [FILE]
  ezr --list            list all commands
  ezr --fast            run quick tests (skip slow)
  ezr --slow            run slow tests only
  ezr --all             run every test
  ezr --help            show this help

A command is the name after `test_`. With no FILE it uses a default
dataset; with a FILE arg it uses that CSV. Examples:
  ezr --tree ../optimiz/auto93.csv
  ezr --classify ../klassif/diabetes.csv
  ezr --learn.budget=256 --acquire20 ../optimiz/auto93.csv
  ezr --core
"""
import sys, random, traceback
from pathlib import Path
from ezr import *

# ---- Default data files (sibling data gists; override via FILE arg) ----
EGOPT1   = Path("../optimiz/auto93.csv")
EGCLASS1 = Path("../klassif/soybean.csv")
EGCLASS2 = Path("../klassif/diabetes.csv")
EGCNB    = Path("../textz/Hall.csv")
EGTXT    = Path("../textz/Hall_raw.csv")

SLOW = {"textmine"}   # commands too slow for the --fast lane

def ready(file):
  """Shuffle, split data into (full, train, test_rows)."""
  d = file if Data == type(file) else Data(csv(str(file)))
  random.shuffle(d.rows)
  half = len(d.rows) // 2
  return (d, clone(d, d.rows[:half][:the.few]), d.rows[half:])

def need(f):
  """Return path string if it exists, else None."""
  p = Path(f)
  if not p.exists():
    print(f"missing: {f}"); return None
  return str(p)

# ============================================================
# Commands: test_<name>(*argv) -- demo + assert, default-or-FILE
# ============================================================

def test_core(*argv):
  """Core primitives: Num, Sym, Data, distance, format."""
  assert o(3.14159).startswith("3.14")
  assert thing("3.14") == 3.14
  t = S(); nest(t, "a.b.c", 42); assert t.a.b.c == 42
  c = adds([10, 20, 30, 40, 50], Num())
  assert c.mu == 30 and 15.8 < spread(c) < 15.9
  c = adds("aaabbc", Sym())
  assert mid(c) == "a" and 1.4 < spread(c) < 1.5
  cols = Cols(["name", "Age", "Weight-"])
  assert not cols.ys[0].heaven and len(cols.xs) == 2 and len(cols.ys) == 1
  f = need(argv[0]) if argv else need(EGOPT1)
  if not f: return
  d = Data(csv(f)); assert len(d.rows) > 0
  assert distx(d, d.rows[0], d.rows[0]) == 0
  ds = [disty(d, r) for r in d.rows]
  assert min(ds) >= 0 and max(ds) <= 1.0001
  print("ok test_core")

def test_tree(*argv):
  """Grow + show a regression tree; check leaves + counterfactual plans."""
  f = need(argv[0]) if argv else need(EGOPT1)
  if not f: return
  _, d_train, _ = ready(f)
  t = treeGrow(d_train, d_train.rows)
  treeShow(t)
  assert t.left is not None and t.right is not None
  d, d_train, _ = ready(f)
  t = treeGrow(d_train, d_train.rows)
  here = treeLeaf(t, max(d.rows, key=lambda r: disty(d, r)))
  plans = sorted(treePlan(t, here))
  assert plans, "treePlan produced no counterfactuals"
  print("ok test_tree")

def test_cluster(*argv):
  """kmeans++ / kmeans / rhalf; show clusters, check sizes."""
  f = need(argv[0]) if argv else need(EGOPT1)
  if not f: return
  d = Data(csv(f))
  cents = kpp(d, k=10); assert len(cents) == 10
  ds = kmeans(d, k=10, cents=cents); assert len(ds) >= 1
  for c in ds:
    print(f"  :n {len(c.rows):>4}  :centroid {o(mids(c))}")
  assert len(rhalf(d, k=10)) >= 1
  print("ok test_cluster")

def test_search(*argv):
  """sa / ls / de optimizers; show energy trace, check it decreases."""
  f = need(argv[0]) if argv else need(EGOPT1)
  if not f: return
  d0 = Data(csv(f)); shuffle(d0.rows)
  known = clone(d0, d0.rows[:50])
  srch  = clone(d0, d0.rows[50:])
  oracle = lambda r: oracleNearest(known, r)
  for name, fn in [("sa", lambda: sa(srch, oracle, budget=500)),
                   ("ls", lambda: ls(srch, oracle, budget=500)),
                   ("de", lambda: de(srch, oracle, budget=2000))]:
    es = [e for _, e, _ in fn()]
    assert es and es[-1] <= es[0], f"{name} regressed: e0={es[0]} eN={es[-1]}"
    print(f"  {name}: {len(es)} improvements, e0={o(es[0])} eN={o(es[-1])}")
  print("ok test_search")

def test_acquire(*argv):
  """Active learning beats a random baseline over 20 reps."""
  f = need(argv[0]) if argv else need(EGOPT1)
  if not f: return
  d0 = Data(csv(f))
  w1, w_rand = Num(), Num()
  win = wins(d0)
  for _ in range(20):
    d, d_train, test_rows = ready(d0)
    lab = acquire(d_train)
    add(w1, win(min(lab.rows[:the.learn.check], key=lambda r: disty(d_train, r))))
    add(w_rand, win(min(sample(test_rows, the.learn.check),
                        key=lambda r: disty(d_train, r))))
  print(f":acquire {int(mid(w1))} :rand {int(mid(w_rand))}")
  assert mid(w1) > mid(w_rand), f"acquire {mid(w1):.1f} <= rand {mid(w_rand):.1f}"
  print("ok test_acquire")

def test_acquire20(*argv):
  """Hold-out win: acquire+tree on one half, tree sorts the other, top-check.
  Prints ONE line `<win> <file>` (win is $1, for `gawk '{print $1}'|sort -n`)."""
  f = need(argv[0]) if argv else need(EGOPT1)
  if not f: return
  w = holdoutWin(Data(csv(f)))
  print(f"{w:.0f}\t{Path(f).name}")
  assert w > 50, f"hold-out win too low: {w}"

def test_classify(*argv):
  """Naive Bayes beats ZeroR (90/10 split, 20 reps)."""
  f = need(argv[0]) if argv else need(EGCLASS2)
  if not f: return
  d = Data(csv(f)); k = d.cols.klass.at
  rows = list(csv(f)); header, body = rows[0], rows[1:]
  def zeroR(train, test):
    cs = {}
    for r in train: cs[r[k]] = cs.get(r[k], 0) + 1
    maj = max(cs, key=cs.get)
    return sum(1 for r in test if r[k] == maj) / (len(test) or 1e-32)
  def nbBatch(train, test):
    h, all = {}, Data([header])
    for r in train:
      w = r[k]; h.setdefault(w, clone(all)); add(all, add(h[w], r))
    ok = 0
    for r in test:
      got = max(h, key=lambda kl: likes(h[kl], r, len(all.rows), len(h)))
      ok += int(got == r[k])
    return ok / (len(test) or 1e-32)
  nb_a, zr_a = [], []
  for i in range(20):
    random.seed(the.seed + i)
    sh = body[:]; random.shuffle(sh)
    sp = int(0.9 * len(sh))
    tr, te = sh[:sp], sh[sp:]
    nb_a.append(nbBatch(tr, te))
    zr_a.append(zeroR(tr, te))
  nb, zr = sum(nb_a)/len(nb_a), sum(zr_a)/len(zr_a)
  print(f":NB {nb:.3f} :ZeroR {zr:.3f}")
  assert nb > zr, f"NB ({nb:.3f}) <= ZeroR ({zr:.3f})"
  print("ok test_classify")

def test_stats(*argv):
  """same / bestRanks / confused."""
  assert same([10,20,30,40,50], [11,19,31,39,51], eps=0.5)
  assert not same([1,2,3,4,5], [100,200,300,400,500], eps=0.5)
  best = bestRanks({"good":[1,2,3], "bad":[100,200,300]})
  assert "good" in best and "bad" not in best
  out = confused({"a":{"a":80,"b":20}, "b":{"a":10,"b":90}})
  for s in out:
    print(f"  :{s.label.strip()} acc={s.acc}")
    assert 0 <= s.acc <= 100
  print("ok test_stats")

def test_textmine(*argv):
  """CNB on processed text + tokenize/tf-idf on raw text. (slow)"""
  f = need(argv[0]) if argv else need(EGCNB)
  if f:
    data = Data(csv(f)); ws = cnb(data); assert len(ws) >= 2
    tmRandom(f)
  g = need(EGTXT)
  if g:
    p = tmPrepare(g); assert len(p.top) >= 20
  print("ok test_textmine")

# ============================================================
# Dispatcher: --<name> runs test_<name>; --key=val sets config
# ============================================================

def runTests(which="all"):
  """Run test_* funcs. which = all | fast (skip SLOW) | slow (only SLOW)."""
  fails = 0
  for name in sorted(globals()):
    if not name.startswith("test_"): continue
    base = name[len("test_"):]
    if which == "fast" and base in SLOW: continue
    if which == "slow" and base not in SLOW: continue
    print(f"--- {name} ---")
    try: globals()[name]()
    except Exception: fails += 1; traceback.print_exc()
  print(f"\nDone. fails={fails}")
  if fails: sys.exit(1)

def list_cmds():
  """Print all commands (test_* funcs)."""
  print("\nCommands (run via --<name> [FILE]):")
  for name in sorted(globals()):
    if name.startswith("test_"):
      doc = (globals()[name].__doc__ or "").splitlines()[0]
      mark = " *slow" if name[len("test_"):] in SLOW else ""
      print(f"  --{name[len('test_'):]:<12} {doc}{mark}")

def main():
  cmd, rest = None, []
  for a in sys.argv[1:]:
    if a.startswith("--") and "=" in a:                  # config: --key=val
      k, v = a[2:].split("=", 1); nest(the, k, thing(v))
    elif a in ("-h", "--help"):  print(__doc__); list_cmds(); return
    elif a == "--list":          list_cmds(); return
    elif a in ("--all", "--fast", "--slow"):
      random.seed(the.seed); runTests(a[2:]); return
    elif a.startswith("--"):     cmd = a[2:]             # command: --name
    else:                        rest.append(a)          # args for the command
  if not cmd:
    print(__doc__); list_cmds(); return
  fn = globals().get(f"test_{cmd}")
  if not fn:
    print(f"unknown: --{cmd}"); list_cmds(); sys.exit(1)
  random.seed(the.seed)
  fn(*rest)

if __name__ == "__main__":
  main()
