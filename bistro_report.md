# BISTRO: The BIS Builds a Swiss Army Knife for Macro Forecasting

**Andrew Tiffin — March 2026**

Central banks spend enormous resources building bespoke forecasting models — a Phillips curve for inflation here, an Okun's law specification for unemployment there, each hand-crafted, estimated, and validated for a single task. When the question changes, the model changes. The BIS thinks there's a better way. Their new open-source model, BISTRO (BIS Time-series Regression Oracle), applies the transformer architecture behind ChatGPT and Claude to macroeconomic time series — and the early results are striking.

## What BISTRO does differently

The core idea is zero-shot forecasting: one model, trained once, applied to any macro forecasting problem without retraining or tuning. A traditional econometrician builds a model per task, like a carpenter reaching for different tools. BISTRO is the Swiss army knife — the same 311-million-parameter transformer handles inflation, GDP, unemployment, and scenario analysis out of the box.

This isn't just a language model repurposed for numbers. Text-based LLMs perform poorly on time series because text and numerical sequences share little structure beyond their sequential nature. BISTRO is built on MOIRAI, a purpose-built multivariate time-series transformer from Woo et al. (2024), fine-tuned on the BIS's own macroeconomic data. The combination matters: training MOIRAI from scratch on BIS data alone yielded weaker results, and MOIRAI off-the-shelf largely ignored covariates on macro data — because only 0.1% of its 27 billion training observations came from economics. Fine-tuning bridges the gap.

## How it works

BISTRO's architecture makes three adaptations that matter for macro forecasting.

**Patches, not observations.** Rather than processing individual data points (the equivalent of characters), BISTRO groups 32 consecutive daily observations into a single "patch" — roughly one month. This is the model's minimal processing unit, analogous to a word in an LLM. The choice of 32 days balances granularity for high-frequency indicators against sufficient context for slower-moving variables like GDP.

**Four-index attention.** The attention mechanism — the component that decides which historical information matters for a given prediction — operates across both time and variables simultaneously. Each attention weight carries four indices: two for series identity and two for time position. Two learned scalars distinguish within-series from cross-series attention, while rotary positional embeddings encode temporal distance between patches. The result is a model that can identify, say, oil price movements leading inflation — without the econometrician having to specify that relationship in advance.

**Mixed-frequency handling.** All 4,925 series in the training data — spanning 63 economies from 1984 to 2024 — are forward-filled to daily frequency with publication lag adjustments. The model only sees data that was actually available at each point in time. No look-ahead bias, no data leakage. The training set mirrors the real-time information environment central bank forecasters actually face.

## Training

The training process is where BISTRO diverges most sharply from traditional econometrics. For each batch, the model samples up to 14 time series, applies a random transformation per series (levels, first differences, log, log-differences), segments into 32-day patches, and masks 1.5–7% of patches from the end. The model learns by predicting the masked values — simulating real forecasting conditions. A temporal consistency mask prevents the model from exploiting forward-filled values that leak across history and prediction windows.

The test design is thoughtful. Rolling windows at 1995, 2005, 2015, and 2023+ capture different economic regimes — pre- and post-Great Recession, low and high inflation environments, structural breaks. This matters: a model that performs well only in tranquil times isn't much use to a central bank.

## What it can do

BISTRO handles both unconditional and conditional forecasting. The unconditional case — predict inflation over the next 12 months given 20 years of history — is straightforward. But the conditional case is where the tool becomes genuinely useful for policymakers. A researcher can produce a baseline inflation forecast, then evaluate how conditioning on different assumptions — a specific oil price path, a particular exchange rate trajectory — modifies that baseline. Scenario analysis without building a new model each time.

The BIS benchmarks BISTRO against an AR(1) model and MOIRAI. The results are competitive for key macro aggregates: inflation, unemployment, GDP growth. But the honest framing is refreshing — the authors treat BISTRO's output as "a strong first estimate" rather than an oracle. When the problem falls squarely within the model's training domain, a tailored econometric model may offer little additional gain. When it doesn't, fine-tuning or bespoke modelling may still be needed.

## Why it matters

The practical significance is less about raw forecasting accuracy and more about access. Smaller central banks with limited machine-learning expertise or computational resources now have an open-source, off-the-shelf tool that produces reliable probabilistic macro forecasts — unconditional and conditional — through a guided Google Colab workflow. No ML engineering required. The code is on GitHub; the instructions are step-by-step.

But there are limitations worth noting. The model is trained on 4,925 series across 63 economies — broad, but not exhaustive. Coverage skews toward exchange rates (1,699 series) and prices (1,130), with thinner representation for labour markets (325), monetary aggregates (235), and demand indicators (83). Countries with sparse data coverage may find the model less reliable. And at 311 million parameters, BISTRO is orders of magnitude smaller than frontier text LLMs — suggesting that a truly universal time-series model remains some distance away.

The BIS is candid about this. A genuinely universal model would likely require trillions of observations and tens of billions of parameters. Until that bar is reached, sectoral foundational models purpose-built for specific domains — like BISTRO for macroeconomics — are the practical alternative. That's an honest assessment, and a useful one.

The upshot: BISTRO won't replace the specialist econometrician working on a specific country forecast. But it substantially lowers the barrier to entry for macro scenario analysis, and it does so at zero cost. For central banks in emerging and developing economies — where modelling capacity is often thin and the forecasting challenges are most acute — that matters.

---

*Source: Koyuncu, Kwon, Lombardi, Perez-Cruz, and Shin (2026), "Introducing BISTRO: a foundational model for unconditional and conditional forecasting of macroeconomic time series," BIS Working Paper No. 1337. Code available at [github.com/bis-med-it/bistro](https://github.com/bis-med-it/bistro).*
