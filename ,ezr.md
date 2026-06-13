<!-- Copyright (c) 2025 Tim Menzies, MIT License https://opensource.org/licenses/MIT -->
<a href="https://timm.fyi"><img align="right" alt="Author" src="https://img.shields.io/badge/Author-timm-dc143c?logo=readme&logoColor=white"></a><img align="right" alt="Language" src="https://img.shields.io/badge/Language-Python-000080?logo=python&logoColor=white"><a href="https://choosealicense.com/licenses/mit/"><img align="right" alt="License" src="https://img.shields.io/badge/License-MIT-32cd32?logo=open-source-initiative&logoColor=white"></a><img align="right" alt="Purpose" src="https://img.shields.io/badge/Purpose-XAI·Optimization-7b68ee?logo=githubcopilot&logoColor=white">

### [http://tiny.cc/ezr](http://tiny.cc/ezr)
ezr.py (v0.5): lightweight XAI for multi-objective optimization. One
self-contained file, Python stdlib only, zero dependencies. Learns a
small explainable tree that finds the best rows in a CSV while
labelling as few examples as it can.

```bash
# install + run on sample data from the optimiz gist
git clone http://tiny.cc/optimiz        # CSV test data (sibling dir)
git clone http://tiny.cc/ezr && cd ezr
python3 ezr.py                          # tree over ../optimiz/auto93.csv
python3 ezr.py -f ../optimiz/SS-A.csv   # any other CSV
```

**Sections:** [NAME](#name) | [SYNOPSIS](#synopsis) | [OPTIONS](#options) | [DATA](#data) | [OUTPUT](#output) | [LICENSE](#license) | [AUTHOR](#author)

## NAME

    ezr - explainable multi-objective optimization, in one file

## SYNOPSIS

    python3 ezr.py [options]
    p                        # konfig bashrc alias: python3 -B ezr.py

    Sibling layout (gists share one parent dir):
      ezr/      this repo
      optimiz/  CSV data (default file = ../optimiz/auto93.csv)
      konfig/   shared Makefile + dotfiles (make help|sh|vi|...)

## OPTIONS

    -a acq=near         label with (near|xploit|xplor|bore|adapt)
    -A Any=4            initial random guesses before learning
    -B Budget=30        labels spent growing the theory
    -C Check=5          budget for checking the learned model
    -D Delta=smed       effect-size test for Cliff's delta
    -F Few=128          sample size for random sampling
    -K Ks=0.95          confidence for Kolmogorov-Smirnov test
    -l leaf=3           min items in a tree leaf
    -m m=1              Bayes low-frequency parameter
    -p p=2              distance coefficient (1,2 = Manhattan,Euclid)
    -s seed=1234567891  random number seed
    -f file=...         data file (default ../optimiz/auto93.csv)
    -h                  show help

## DATA

    CSV with a self-describing header (see optimiz):
      Upper first char -> numeric column
      lower first char -> symbolic column
      suffix +         -> numeric goal, maximize
      suffix -         -> numeric goal, minimize
      suffix X         -> ignore
      missing value    -> '?'

## OUTPUT

    Prints an explainable tree: each branch is a rule, indented by
    depth; `win` scores how good the rows under that rule are (higher
    = closer to all goals). The footer lists the columns actually used.

## LICENSE

    MIT. https://choosealicense.com/licenses/mit/

## AUTHOR

    Tim Menzies <timm@ieee.org>
