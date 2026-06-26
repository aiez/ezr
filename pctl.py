#!/usr/bin/env python3 -B
"Read 'land rand verdict file' lines; tally wins + percentiles."
import sys
xs = [l.split() for l in sys.stdin if len(l.split()) >= 4]
n  = len(xs) or 1
col = lambda i: sorted(float(r[i]) for r in xs
                       if abs(float(r[i])) < 1e4)
p   = lambda v: [v[min(len(v)-1, int(q/100*len(v)))]
                 for q in (10,30,50,70,90)]
f   = lambda nm,v: print("%-10s %5.1f %5.1f %5.1f %5.1f %5.1f"
                         % (nm, *p(v)))
print("\nn=%d datasets   STAT WINS (Cliff's delta + KS)" % n)
for v in ("land", "rand", "tie"):
  c = sum(r[2] == v for r in xs)
  print("  %-5s %3d  %4.1f%%" % (v, c, 100*c/n))
print("\n%-10s %5s %5s %5s %5s %5s" % ("WIN pct","10","30","50","70","90"))
f("landscape", col(0)); f("random", col(1))
