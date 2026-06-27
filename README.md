<!-- Copyright (c) 2026 Tim Menzies, MIT License https://opensource.org/licenses/MIT -->
<a href="https://timm.fyi"><img align="right" alt="Author" src="https://img.shields.io/badge/Author-timm-dc143c?logo=readme&logoColor=white"></a><img align="right" alt="Language" src="https://img.shields.io/badge/Language-Python%203.12+-000080?logo=python&logoColor=white"><img align="right" alt="Deps" src="https://img.shields.io/badge/Deps-0-32cd32?logo=checkmarx&logoColor=white"><a href="https://choosealicense.com/licenses/mit/"><img align="right" alt="License" src="https://img.shields.io/badge/License-MIT-32cd32?logo=open-source-initiative&logoColor=white"></a><img align="right" alt="Purpose" src="https://img.shields.io/badge/Purpose-XAI·Optimization-7b68ee?logo=githubcopilot&logoColor=white">

### [http://tiny.cc/ezr](http://tiny.cc/ezr)
ezr — explainable multi-objective optimization. Two files, ~1100 lines,
**zero dependencies**, pure Python stdlib. An experiment in "how low can
you go?": active learning labels a few dozen informative rows, builds a
regression tree, and sorts the rest. Repeated studies show that labelling
just the first ~5 examples optimizes as well or better than SMAC — at two
orders of magnitude less cost.

```bash
# sibling data gists supply the CSVs (no data lives in here)
git clone http://tiny.cc/optimiz       # optimization data
git clone http://tiny.cc/klassif       # classification data
git clone http://tiny.cc/ezr && cd ezr
python3 cli.py --list                  # all commands
python3 cli.py --tree ../optimiz/auto93.csv
python3 cli.py --all                   # run every self-test
```

**Sections:** [NAME](#name) | [SYNOPSIS](#synopsis) | [DESCRIPTION](#description) | [DATA](#data) | [COMMANDS](#commands) | [OPTIONS](#options) | [LAYOUT](#layout) | [LICENSE](#license) | [AUTHOR](#author)

**Files:** [ezr.py](http://tiny.cc/ezr#file-ezr-py) | [cli.py](http://tiny.cc/ezr#file-cli-py) | [Makefile](http://tiny.cc/ezr#file-makefile) | [pyproject.toml](http://tiny.cc/ezr#file-pyproject-toml) | [LICENSE.md](http://tiny.cc/ezr#file-license-md)

## NAME

    ezr - explainable multi-objective optimization via decision
          trees, clustering, naive bayes, and active learning

## SYNOPSIS

    python3 cli.py [--key=val ...] --<name> [FILE]
    python3 cli.py --list | --fast | --slow | --all | --help
    p                          # konfig bashrc alias: python3 -B cli.py

    Sibling gists (one parent dir; no naked paths):
      ezr/      this repo (ezr.py library + cli.py dispatch)
      optimiz/  optimization CSVs   (tiny.cc/optimiz)
      klassif/  classification CSVs (tiny.cc/klassif)
      textz/    text-mining CSVs    (tiny.cc/textz)
      konfig/   shared Makefile + dotfiles (make help|sh|vi|...)

## DESCRIPTION

    Summarizes CSV into Num/Sym columns; grows decision trees that
    minimize distance to the ideal outcome; clusters via k-means or
    recursive halving; classifies + actively learns with naive bayes
    or centroid acquisition. Input is CSV; the header defines roles
    (see DATA). Stdlib only, Python 3.12+.

## DATA

    Header column names declare each role:
      [A-Z]*    numeric        (e.g. "Age")
      [a-z]*    symbolic       (e.g. "job")
      [A-Z]*+   maximize goal  (e.g. "Mpg+")
      [A-Z]*-   minimize goal  (e.g. "Lbs-")
      [a-z]*!   class label    (e.g. "sick!")
      *X        ignored        (e.g. "idX")
      ?         missing value  (in rows, not the header)

## COMMANDS

    each `test_<name>` in cli.py is one command (demo + self-check),
    run via `--<name>`. No FILE -> default dataset; FILE -> that CSV.
      --core       primitives: Num/Sym/Data/distance/format
      --tree       grow + show a regression tree, check plans
      --cluster    k-means++ / k-means / recursive halving
      --classify   naive bayes beats ZeroR        (needs ../klassif)
      --search     sa | ls | de optimizers (energy trace)
      --acquire    active learning beats random (20 reps)
      --acquire20  hold-out tree win (acquire half, sort the other)
      --textmine   CNB + tf-idf text mining        (needs ../textz)
      --stats      same / bestRanks / confused
    lanes: --fast (skip slow) | --slow (textmine) | --all

## OPTIONS

    --seed=1            random seed
    --p=2               distance (1,2 = Manhattan, Euclid)
    --few=128           max rows kept while sampling
    --learn.leaf=3      examples per tree leaf
    --learn.start=4     initial labels
    --learn.budget=50   rows allowed to be labelled
    --learn.check=5     guesses to check
    --bayes.m=2         m-estimate    --bayes.k=1   laplace
    (full list: head of ezr.py; override any as --key=val)

## LAYOUT

    ezr.py   library; section banners per app (Types, Col, Data,
             Distance, Bayes, Tree, Cluster, Classify, Search,
             Acquire, Textmine, Stats, Format)
    cli.py   dispatch; one test_<name> per concept (demo + assert),
             run via --<name>; --fast/--slow/--all lanes

## LICENSE

    MIT. https://choosealicense.com/licenses/mit/

## AUTHOR

    Tim Menzies <timm@ieee.org>
