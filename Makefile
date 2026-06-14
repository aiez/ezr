# vim: ts=2 sw=2 sts=2 et :
# knobs only; shared targets live in $(KONFIG)/Makefile
KONFIG ?= ../konfig
APP    := ezr
MAIN   := cli.py
EXT    := py
LANG   := python
SRC    := *.py
LINT   := ruff check ezr.py cli.py
TOOLS  := python3:run ruff:lint
PKG    := python3 gawk ruff neovim tmux

$(KONFIG)/Makefile:
	@test -f $@ || { echo "missing konfig: git clone http://tiny.cc/konfig $(KONFIG)"; exit 1; }
include $(KONFIG)/Makefile

# ---- test lanes + benchmark (repo-specific; after the include) ----
DATA ?= ../optimiz
JOBS ?= 24

test:    ## quick tests (skips slow textmine)
	@python3 -B cli.py --fast
slow:    ## slow tests only (textmine)
	@python3 -B cli.py --slow
testall: ## every test (fast + slow)
	@python3 -B cli.py --all
win: ## hold-out win across every $(DATA)/*.csv (parallel): sorted list + mean
	@ls $(DATA)/*.csv | sort -R | \
	 xargs -P $(JOBS) -I{} sh -c 'python3 -B cli.py --acquire20 "{}" 2>/dev/null' \
	 | gawk '{print $$1}' | sort -n | tee /tmp/ezr_win.txt | fmt
	@gawk '{n++;s+=$$1} END{if(n) printf "\nmean=%.1f n=%d\n", s/n, n}' /tmp/ezr_win.txt
