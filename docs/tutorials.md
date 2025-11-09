# Prediction Market Maker Tutorial

## Contents

This is the tutorial that explains the codebase.
1. [How the parts fit](#how-the-parts-fit-1-minute)
2. [The modules](#the-modules)
3. [Mini examples](#mini-examples)
4. [Tiny FAQ](#tiny-faq)
5. [Pricing (math)](#pricing-explained-with-simple-math)
6. [Strategy (math)](#strategy-explained-with-simple-math)
7. [Kid-friendly story](#kid-friendly-story-version)
8. [PnL & risk reasoning](#using-math-to-reason-about-pnl-and-risk)
9. [Worked micro-examples](#worked-micro-examples)
10. [Cheat sheet](#cheat-sheet)

## How the parts fit

1. A Venue (like a pretend exchange) gives you an order book snapshot.
2. A Strategy looks at the snapshot and decides two prices: a bid (buy) and an ask (sell).
3. The Router sends those orders to the Venue.
4. The Venue tells you which orders got filled (Trades).
5. The Store updates your Inventory; Risk/metrics can check safety and stats.

## The modules

- core/ — The “lego bricks.”
  - Types like Order, Trade, Market, and a little math help. Think of these as the pieces that everything else snaps onto.

- venue/ — The “store.”
  - base.py is the rules of the store. mock.py is a tiny pretend store that always has one price level. You place orders here.

- pricing/ — The “calculator.”
  - lmsr.py is a smart calculator (LMSR) that turns “how many people own YES/NO” into fair prices. inventory.py nudges prices if you already own a lot so you don’t get too unbalanced.

- strategy/ — The “brain.”
  - binary_mm.py looks at the mid-price and inventory and says: “I’ll buy near here, and sell a little higher,” with a safe gap (spread) in between.

- risk/ — The “seatbelt.”
  - limits.py and kill_switch.py keep you from going too big or losing too much.

- exec/ — The “delivery driver.”
  - router.py takes the orders from the brain to the store. throttle.py makes sure you don’t spam the store too fast.

- state/ — The “notebook.”
  - store.py keeps track of your markets and inventory. book.py remembers recent order books.

- backtest/ — The “time machine.”
  - scenarios.py makes pretend price paths; engine.py plays them forward so you can see what would have happened.

- io/ — The “scoreboard and save box.”
  - metrics.py exports counters if you install Prometheus. persistence.py is a hook to save things later.

- app/ — The “wires.”
  - main.py connects the parts. run_backtest.py and run_live.py are quick starters you can run.

## Mini examples

These use the in-repo imports (`from src...`) so you can copy-paste and run without installing the package. If you installed the wheel, replace `src.` with `prediction_market_maker.`.

### 1) Make a simple two-sided quote

```python
from src.strategy.binary_mm import BinaryMMStrategy
from src.core.types import OrderBookSnapshot, BookLevel

strat = BinaryMMStrategy(spread_bps=100)  # total spread = 1%, half on each side
book = OrderBookSnapshot(
    market_id="EVT",
    bids=[BookLevel(0.49, 100)],
    asks=[BookLevel(0.51, 100)],
)
orders = strat.quote(book)
for o in orders:
    print(o.side, o.price, o.qty)
```

What’s happening: The strategy sees a mid of ~0.50, then places a buy a bit below and a sell a bit above (rounded to ticks) so the buy price is always less than the sell price.

### 2) See inventory nudge the prices

```python
from src.strategy.binary_mm import BinaryMMStrategy
from src.core.types import OrderBookSnapshot, BookLevel

strat = BinaryMMStrategy(spread_bps=100, inventory_alpha=0.01)
strat.update_inventory(+30)  # we’re long 30 YES; strategy will try to sell a bit more expensive
book = OrderBookSnapshot(
    market_id="EVT",
    bids=[BookLevel(0.49, 100)],
    asks=[BookLevel(0.51, 100)],
)
orders = strat.quote(book)
for o in orders:
    print(o.side, o.price, o.qty)
```

What’s happening: Since you already own a lot of YES, the “calculator” nudges your fair YES price down a touch, so your sell (ask) gets a bit more attractive and your buy (bid) gets a bit less eager. This helps you rebalance.

### 3) Tiny backtest in ~10 lines

```python
from src.app.main import build_mock_environment
from src.backtest.engine import run_scenario
from src.backtest.scenarios import random_walk

store, venue, strat = build_mock_environment()
scenario = random_walk(steps=50, start=0.5, sigma=0.03, seed=42)
run_scenario(store, venue, strat, scenario)
print("Final net YES:", store.inventory.net_yes("YES_2025_EVENT"))
```

You just walked the market around randomly and let the brain keep quoting. The notebook (state) updated inventory with each fill.

## Tiny FAQ

- Why is bid always lower than ask?
  The strategy keeps a “spread” (safety gap) and rounds prices so they don’t collapse into the same number.

- What if the book is empty?
  The strategy falls back to 0.50 (a fair coin) so it can still quote.

- Can I use a different pricing model?
  Yes—add a class in `pricing/` and plug it into your strategy.

## What is pricing?

Think of a binary contract (YES pays 1 if event happens, else 0). A fair price is just a probability between 0 and 1.

### LMSR (Logarithmic Market Scoring Rule)

- Cost function (how much a trader must pay to change quantities):

  `C(q) = b * log( exp(q_yes / b) + exp(q_no / b) )`

- Marginal price (what one more YES share should cost):

  `p_yes = exp(q_yes / b) / ( exp(q_yes / b) + exp(q_no / b) )`

  For two outcomes, this is a softmax: prices are positive and sum to 1.

- Intuition for `b` (liquidity):
  - Bigger `b` = prices move more slowly when quantities change (deeper market).
  - Smaller `b` = prices move quickly (shallow market).

- Binary shortcut (in terms of difference Δ = q_yes − q_no):

  `p_yes = 1 / (1 + exp(−Δ / b))` (a logistic/sigmoid curve)

Use LMSR when you want a smooth, principled mapping from inventory to probability.

### CPMM (Constant Product) — high-level

- For two pools with reserves `R_yes` and `R_no`, keep product `R_yes * R_no = k` roughly constant.
- Marginal price of YES increases when `R_yes` is scarce vs `R_no`.
- A simple proxy for a “probability-like” price is:

  `p_yes ≈ R_no / (R_yes + R_no)`

- Trading moves reserves, which shifts the price; exact trade costs depend on how you enforce the invariant.

Use CPMM when quoting against AMM-style venues (e.g., Polymarket) where reserves determine price.

### Inventory skew (keep balance)

Our code uses a simple, linear nudge to probabilities based on your net YES:

- Start with base probs from mid: `[p_yes, p_no] = [m, 1 − m]`.
- Nudge with inventory `inv` and small factor `α`:

  `p_yes' = p_yes − α * inv`

  `p_no'  = p_no  + α * inv`

- Renormalize and clamp to [0, 1]. If you’re long a lot of YES (`inv > 0`), your adjusted YES probability goes down a bit, so you quote a slightly higher ask and lower bid to encourage selling.

This is not the only choice—you can also skew in logit space for nicer behavior near 0/1.

## Strategy, explained with simple math

Binary market-making (our `BinaryMMStrategy`) follows a few steps:

1) Estimate fair probability from the book:

- Mid-price: `m = (best_bid + best_ask) / 2` (fallback to 0.5 if missing)
- Base probabilities: `[m, 1 − m]`

2) Apply inventory skew:

- Get `p_yes` after skewing (see above).

3) Turn a total spread (in basis points) into bid/ask around `p_yes`:

- Total spread in bps = `S`. Half-spread in price = `S / 20000` (because 100 bps = 1%).
- Raw quotes:

  `bid_raw = max(0, p_yes − half_spread)`

  `ask_raw = min(1, p_yes + half_spread)`

4) Round to tick and keep bid < ask:

- `bid = floor_to_tick(bid_raw)`; `ask = ceil_to_tick(ask_raw)`
- If equal, widen a tiny bit so `bid < ask`.

That’s it: two-sided quotes with a safety gap, nudged by your inventory.

### Dumb Me Version

Imagine you run a tiny candy stand:

- People ask: "Will it rain tomorrow?" YES ticket pays 1 candy if it rains.
- You don’t know for sure, so you guess the chance (like 50%).
- You say: "I’ll BUY a ticket from you for 0.49 candies, and SELL one to you for 0.51 candies."
- That little gap (0.02 candies) is how you stay in business.
- If you already own a mountain of YES tickets, you lower how much you pay (maybe 0.47) and raise how much you sell for (maybe 0.53) so you don’t drown in YES.

The pricing models help your guess be smart instead of random.

### LMSR like jars

Two jars: YES tickets and NO tickets.
If the YES jar gets more tickets, YES becomes more expensive (closer to 1). If it gets fewer, price slides toward 0.
`b` is jar “softness”: big soft jar hardly moves when you add a ticket.

### CPMM like buckets

Two buckets of colored water: blue (YES) and red (NO). Product of amounts wants to stay close. If blue bucket gets drained, blue water is precious so YES price rises.

### Inventory skew like balance scale

If your side of the scale has lots of YES weight, you tip it slightly so new YES doesn’t pile on—making your YES price less shiny to buyers.

### Spread like a cushion

You put a cushion between buy and sell so you’re not guessing the exact true price every second—this protects you from being instantly picked off when the world changes.

## Using math to reason about PnL and risk

- Expected value (EV) of buying YES at price `p_quote` when true probability is `p_true`:

  `EV ≈ (p_true − p_quote) * qty`

  If you sell, flip the sign: `EV ≈ (p_quote − p_true) * qty`.

- Inventory value (mark-to-market):

  `Value ≈ position_yes * p_true`

- “Delta” (sensitivity):

  `d(Value)/d(p_true) = position_yes`

  That’s why we limit position—big position means big swings when beliefs move.

- Spread vs fill rate trade-off:
  - Wider spread ⇒ more edge per fill but fewer fills.
  - Narrower spread ⇒ more fills but less edge; higher risk of adverse selection.

## Worked micro-examples

1) No inventory, `m = 0.50`, spread = 100 bps (1% total)

- `half_spread = 0.005` ⇒ `bid = 0.495`, `ask = 0.505` (after tick rounding)

2) Long 30 YES, `α = 0.01`

- Skew: `p_yes' = 0.50 − 0.01*30 = 0.20` (then renormalize with `p_no' = 0.80`)
- Quotes around 0.20: `bid ≈ 0.195`, `ask ≈ 0.205`
- You’re now more eager to sell than buy (as intended).

3) LMSR intuition: if `Δ = q_yes − q_no = 100` and `b = 50`

- `p_yes = 1 / (1 + exp(−Δ/b)) = 1 / (1 + exp(−2)) ≈ 0.88`
- A large positive Δ (more outstanding YES) pushes price up.

## Cheat sheet

- Total spread (bps) ⇒ half-spread (price): `half = bps / 20000`
- Always round: `bid = floor_to_tick(...)`, `ask = ceil_to_tick(...)`
- EV of a trade (buy): `(p_true − price) * qty`
- LMSR price (binary): `p_yes = 1 / (1 + exp(−(q_yes − q_no)/b))`


