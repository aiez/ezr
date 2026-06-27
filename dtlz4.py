#!/usr/bin/env python3 -B
"""
dtlz4.py: drive ezr2 with an EXTERNAL MODEL instead of a CSV.

  1. build a data file of random x-values with "?" for the goals;
  2. redefine ezr2.labelled() so a row's goals come from a model;
  3. optimize, labelling at most --budget rows.

  python3 dtlz4.py
"""
import random, ezr2
from math import cos, sin, pi

N = 6                                  # decision vars x1..x6 (>4); 2 goals

def dtlz4(x):
  "The model: x in [0,1]^N -> two objectives to MINIMIZE."
  g  = sum((v - 0.5) ** 2 for v in x[1:])
  th = x[0] ** 100 * pi / 2            # 100 = DTLZ4's sampling bias
  return [(1 + g) * cos(th), (1 + g) * sin(th)]

# Header roles (see ezr2's DATA note): X* are numeric inputs, F*-
# are goals to minimize. Each row is random x with goals unmeasured.
names = [f"X{i+1}" for i in range(N)] + ["F1-", "F2-"]
def pool(n=1000):
  return [[random.random() for _ in range(N)] + ["?", "?"] for _ in range(n)]

def labelled(row):
  "ezr2's seam: fill a row's goals from the model, and fold them into"
  "data.cols so disty can normalize objectives as labels arrive."
  if "?" in row[N:]:
    row[N:] = dtlz4(row[:N])
    for at in data.y: data.cols[at] = ezr2.add(data.cols[at], row[at])
  return row
ezr2.labelled = labelled                # labelled() reads the global `data`

def instance(row):
  # Show one labelled row: its x (the decision) and goals. disty of an
  # already-labelled row costs no new model runs, so we stay in budget
  # (we avoid ezr2.wins(), which would label the whole pool).
  print("  x  " + " ".join("%.2f" % v for v in row[:N]))
  print("  f  " + " ".join("%.3f" % v for v in row[N:]) +
        "   (disty %.3f, lower=better)" % ezr2.disty(data, row))

ezr2.the.budget = 30

# (1) THE BEST INSTANCE: landscape() ranks the whole pool, returns the
# best rows it found within the label budget.
random.seed(1); data = ezr2.Data([names] + pool())
got = ezr2.landscape(data)
print("the best option found (one instance):")
instance(got[0])

# (2) AN EXPLANATORY MODEL: a tree saying which x-ranges win. The win
# column is relative only to the rows we labelled (so, in budget).
print("\nwhy? an explanatory model -- which x-ranges reach good goals:")
ezr2.show(data, ezr2.tree(data, got))

# (3) TEST THE MODEL ON NEW DATA: holdout() learns the tree on a train
# split, then uses it to pick the best row from an UNSEEN test split.
random.seed(1); data = ezr2.Data([names] + pool())
print("\ndoes that model generalize? best pick on unseen test data:")
instance(ezr2.holdout(data))
