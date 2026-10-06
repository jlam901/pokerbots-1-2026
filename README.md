# MIT Pokerbots 2026

Team bot for the [MIT Pokerbots](https://pokerbots.org) 2026 competition, built by Justin Lam ([@jlam901](https://github.com/jlam901)), Azjargal Ganbold ([@azjargal-g](https://github.com/azjargal-g)), and Danny Thach. The team finished in the top 25% of teams.

## The game

This year's variant is heads-up hold'em with a twist: each player is dealt **3 hole cards** preflop and must **discard one face up** after the flop. Bots play thousands of hands per match against other teams' bots under a time limit.

## Where things are

| Branch | What's there |
|---|---|
| `Agent-1.2` | **Final competition bot** (`python_skeleton/player.py`) and the preflop charts it loads |
| `cfr-attempt` | Preflop chart pipeline, plus a post-competition CFR+ implementation |
| `Agent-1`, `Agent-1.0` | Earlier versions of the competition bot |
| `main` | Engine and setup |

## Competition bot (`Agent-1.2`)

- **Preflop:** looks up the hand's simulated win rate in one of three charts (offsuit, two suited, three suited) and maps it to a betting tier with a raise target and a call cap.
- **Discard:** keeps cards that make a flush draw, an open-ended straight draw, or a pair, and discards the weakest remaining card.
- **Postflop:** classifies the best 5-card hand (top pair through quads) and bets toward a per-category target contribution. Targets adapt during the match depending on whether the opponent folds to our raises.
- **Opponent modeling:** tracks the opponent's bet sizes and folds weaker hands against bets in the top percentiles of their history.

## Preflop charts (my work)

`cfr-attempt/python_skeleton_checkcall/`

1. `run_checkcall_sim.py` runs the engine with two check-call bots, producing a game log of millions of hands.
2. `build_preflop_chart.py` parses the log and records, for every 3-card hand class, how often it won.
3. The output is three CSV charts covering **1,183 hand classes from about 2.2M simulated hands**, which the competition bot uses for its preflop decisions.

Note: these are win rates in check-call self-play (every hand goes to showdown), not equity against a realistic opponent range.

## CFR+ (post-competition, my work)

`cfr-attempt/python_skeleton/`, written after the competition ended to replace the heuristic strategy.

- `cfr_core.py`: CFR+ with regret matching (regrets clipped at zero), average-strategy tracking, and node pruning (3M-node cap)
- `cfr_info_set.py`: information-set abstraction, bucketing hands into 10 strength classes
- `cfr_game_tree.py`: game tree with raise sizes abstracted to min-raise and all-in, plus chance sampling
- `cfr_trainer.py`: self-play training loop with checkpointing and resume
- `player.py`: loads a trained strategy in the background and falls back to the heuristic bot if none is available

Train with:

```bash
cd python_skeleton
python cfr_trainer.py <iterations> [save_path] [--resume]
```

## Setup

The engine runs in Python and uses [`uv`](https://docs.astral.sh/uv/) for packages and virtual environments.

**1. Install uv**

```bash
# macOS or Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

On Windows, use WSL (Ubuntu works) and run the Linux command inside it. You can also install natively with `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`.

**2. Create the environment and install dependencies**

From the repo root:

```bash
uv venv    # optionally pick a version: uv venv --python 3.13.3 (needs >= 3.8)
uv sync    # installs cython 3.2.3 and pkrbot 1.0.4 (hand evaluation)
```

uv downloads a suitable Python version automatically if you don't have one.

**3. Run a match**

```bash
git checkout Agent-1.2         # or cfr-attempt for the CFR version
.venv/bin/python engine.py
```

Edit `config.py` to choose which bots play each other. Game logs are written to the repo root.

The engine and skeleton code are from the [MIT Pokerbots 2026 engine](https://github.com/mitpokerbots/engine-2026).
