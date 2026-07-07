#!/usr/bin/env python3 -B
"""
Growing.py: sensitivity of landscape's keepf/grow knobs (see Growing.md).

SWAY [Chen'18] used keepf=0.5, grow=2; ezr2 defaults to 0.66, 4.
We draw 100,000 random (keepf, grow) points from the grid
keepf in {0.50..0.80}, grow in {2..10}, over 20 datasets x 20 seeds, and
record the win DELTA vs the SWAY baseline (0.5, 2) on the same
dataset+seed. The baseline grid point reads exactly 0.
Output: Growing.png heat map + an ASCII grid on stdout.
"""
import glob, random, ezr2
from ezr2 import Data, csv, some, wins, landscape, the
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

N        = 100_000
SEEDS    = range(20)
CAP      = 256
GROWS    = list(range(2, 11))                          # 2..10 (9 cols)
KEEPFS   = [0.5,0.55,0.6,0.65,0.7,0.75,0.8]            # exact keepf (7 rows)
the.landscape = "active"

# 20 fast datasets (few columns, enough rows)
files = []
for f in sorted(glob.glob(f"{ezr2.DOOT}/optimiz/*.csv")):  # PATHS: via DOOT
  with open(f) as fh: cols = len(fh.readline().split(","))
  if cols <= 16: files.append(f)
files = files[:20]

data, W = {}, {}
for f in files:
  d = Data(csv(f)); d.rows = some(d.rows, CAP)
  data[f] = d; W[f] = wins(d)

def win(f, keepf, grow, seed):
  the.keepf, the.grow = keepf, grow
  random.seed(seed)
  return W[f](landscape(data[f])[0])

# baseline (SWAY: keepf=0.5, grow=2) cached per (dataset, seed)
base = {(f,s): win(f, 0.5, 2, s) for f in files for s in SEEDS}

ssum = [[0.0]*len(GROWS) for _ in KEEPFS]
scnt = [[0  ]*len(GROWS) for _ in KEEPFS]
rng  = random.Random(0)
for _ in range(N):
  f = rng.choice(files); s = rng.choice(list(SEEDS))
  keepf = rng.choice(KEEPFS); grow = rng.randint(2, 10)
  d = win(f, keepf, grow, s) - base[(f,s)]
  i, j = KEEPFS.index(keepf), grow-2
  ssum[i][j] += d; scnt[i][j] += 1

grid = [[(ssum[i][j]/scnt[i][j] if scnt[i][j] else 0.0)
         for j in range(len(GROWS))] for i in range(len(KEEPFS))]

# --- ASCII grid ---  (rows high->low so keepf=0.5 is at the bottom,
#  matching Growing.png's origin="lower"; baseline cell is exactly 0)
print("delta win vs SWAY baseline (keepf=0.5, grow=2), N=%d\n" % N)
print("keepf\\grow " + " ".join("%4d" % g for g in GROWS))
for i in reversed(range(len(KEEPFS))):
  print("%-9s " % ("%.2f" % KEEPFS[i]) + " ".join("%4.0f" % grid[i][j]
                                                  for j in range(len(GROWS))))
flat = [grid[i][j] for i in range(len(KEEPFS)) for j in range(len(GROWS))]
print("\nbest cell %.0f   worst cell %.0f   mean %.1f" %
      (max(flat), min(flat), sum(flat)/len(flat)))

# --- heat map ---
M = max(abs(min(flat)), abs(max(flat)))
fig, ax = plt.subplots(figsize=(7,4))
im = ax.imshow(grid, aspect="auto", origin="lower", cmap="RdBu",
               vmin=-M, vmax=M)
ax.set_xticks(range(len(GROWS))); ax.set_xticklabels(GROWS)
ax.set_yticks(range(len(KEEPFS)))
ax.set_yticklabels(["%.2f"%k for k in KEEPFS])
ax.set_xlabel("grow (labels per round)"); ax.set_ylabel("keepf (kept fraction)")
ax.set_title("Win delta vs SWAY baseline (keepf=0.5, grow=2)")
for i in range(len(KEEPFS)):
  for j in range(len(GROWS)):
    c = "white" if abs(grid[i][j]) > 0.6*M else "black"   # contrast on dark cells
    ax.text(j, i, "%.0f"%grid[i][j], ha="center", va="center",
            fontsize=8, color=c)
fig.colorbar(im, label="mean win delta")
fig.tight_layout(); fig.savefig("Growing.png", dpi=130)
print("\nwrote Growing.png")
