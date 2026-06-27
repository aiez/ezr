# Is Random as Good as Anything?

A recurring worry in active learning: on a single easy dataset, **random
sampling looks as good as a clever acquisition function**. If true, four years
of active-learning research collapses. This note tests it on 129 SE
optimization datasets and finds it false — but only once you (1) fix a bug,
(2) ignore the mean, and (3) read the tail.

## The scare

On `misc_auto93.csv` (~400 rows), 20 shuffles of active landscape vs a
same-budget random pick:

```
random wins 10,  active wins 6,  tie 4
```

Random *beat* active. But auto93 is tiny and easy: every method lands at
disty 0.075–0.17. When the good corner is trivially reachable, nothing
separates. One easy dataset proves nothing.

## The proper test

`ezr2.py holdouts|pure` runs active vs random over a whole corpus (20 seeds
each, `same()` verdict per dataset). First run silently dropped 34/129
datasets — **a bug, not weak results**.

**Bug.** The split criterion derives the right-hand variance by subtraction
(`mix(tot, me, -1)`). Floating-point underflows `m2` slightly negative;
`sd = sqrt(m2)` then returns a *complex* number and crashes. The old
sum-of-`m2` criterion never took a square root, so the fault was latent until
we switched to a uniform `var = sd | entropy` criterion. Fixed by clamping
`m2 >= 0` at the source. All 129 now run.

## Verdict (129/129)

| lane | active | tie | random |
|------|-------:|----:|-------:|
| holdouts (tree)   | 41 | 74 | 14 |
| pure (no tree)    | 55 | 53 | 21 |

Active beats random **~3:1** in both. But ~half the corpus **ties** — the
sparsity ceiling: most datasets put the good rows in a small corner any
competent method reaches. This is why the *means* look flat (pure: 79.5 vs
78.6).

## The mean lies; the tail tells

Pure-search win, by percentile (low win = hard dataset):

```
WIN pct       10    30    50    70    90
active      72.3  87.3  94.0  97.3  99.9
random      68.7  83.8  92.9  96.2  99.9
gap         +3.6  +3.5  +1.1  +1.1   0.0
```

The advantage is **monotonic in difficulty**. Active does not make easy
problems easier (p90: both maxed out); it **rescues the hard ones** (p10/p30).
Averaging over the easy ceiling washes out an edge that is real and
concentrated in the tail. *Report the distribution, not the mean.*

## A cost of interpretability

The tree lane (learn on train split, pick from unseen test split) muddies
the tail:

```
WIN pct       10    30    50    70    90
active      50.6  72.6  86.1  94.9  99.4
random      52.1  68.7  86.2  92.3  99.6
gap         -1.5  +3.9  -0.1  +2.6  -0.2
```

Active wins the mid-tail but **loses at p10**. The hold-out pick is a
high-variance estimator, and the hardest datasets are often the smallest, so
its noise erases active's edge exactly where data is thinnest. The tree buys
interpretability (which x-ranges win); on thin, hard data that is **not free**.

## Conclusion

Random is **not** as good as anything. It ties on the easy majority (ceiling),
but where separation is possible active wins ~3:1, with its advantage growing
as problems get harder. The illusion of parity comes from three mistakes:
trusting one easy dataset, letting a crash silently drop hard datasets, and
reading the mean instead of the tail.
