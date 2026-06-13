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
python3 cli.py tree ../optimiz/auto93.csv
python3 cli.py test_all                # run every self-test
```

**Sections:** [NAME](#name) | [SYNOPSIS](#synopsis) | [DESCRIPTION](#description) | [DATA](#data) | [COMMANDS](#commands) | [OPTIONS](#options) | [LAYOUT](#layout) | [LICENSE](#license) | [AUTHOR](#author)

**Files:** [ezr.py](#file-ezr-py) | [cli.py](#file-cli-py) | [Makefile](#file-makefile) | [pyproject.toml](#file-pyproject-toml) | [LICENSE.md](#file-license-md)

## NAME

    ezr - explainable multi-objective optimization via decision
          trees, clustering, naive bayes, and active learning

## SYNOPSIS

    python3 cli.py [--key=val ...] CMD [args]
    python3 cli.py --list | --help
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

    each `eg_<app>` in cli.py is a command; `eg_test_<app>` is a test.
      tree      grow + show a regression tree
      cluster   k-means++ / recursive halving
      classify  incremental naive bayes (confusion matrix)
      search    sa | ls | de optimizers (energy trace)
      acquire   active learning; top rows by distance-to-heaven
      textmine  CNB text mining (needs ../textz)
      stats     same / bestRanks / confused demo
      test_all  run every self-test (no pytest needed)

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
    cli.py   dispatch; eg_<app> demos + eg_test_<app> tests

## LICENSE

    MIT. https://choosealicense.com/licenses/mit/

## AUTHOR

    Tim Menzies <timm@ieee.org>
