# First public collector run

**Run date:** 2026-10-10 UTC (2026-10-11 in Europe/Paris)  
**Runtime:** Python 3.13.15, uv 0.13.0, Windows x86_64  
**Venue/API:** Kalshi public REST; no credentials or order-entry endpoints used.

## Commands and observations

The environment resolved and installed the package and dependencies with `uv sync --python <Python 3.13 interpreter>`.

Market discovery ran with:

```shell
uv run --python <Python 3.13 interpreter> weather-mm markets --series-ticker KXHIGHNY --max-markets 100
```

Observed result: HTTP 200, one page, 12 markets. The response was appended to the local capture file. One currently listed market selected for the snapshot was `KXHIGHNY-26OCT11-B68.5`.

Snapshot command:

```shell
uv run --python <Python 3.13 interpreter> weather-mm snapshot --ticker KXHIGHNY-26OCT11-B68.5 --depth 0
```

Observed result: HTTP 200. The response contained `orderbook_fp` with `yes_dollars` and `no_dollars` levels; the captured response had 1 YES level and 48 NO levels. Client receive time was 2026-10-10T23:26:31Z. Canonical payload SHA-256:

```text
2613870d9840180715c8a7a5dc313e9696ce0a8ba7eb1067d3f65c186959e590
```

The local JSONL contained two parseable response records (market list and order-book snapshot) and was 35,993 bytes. It remains excluded from Git because it is raw captured data.

## Setup issue and resolution

The first two `uv sync` attempts failed during uv-managed Python interpreter setup with a missing expected target directory error (first Python 3.15, then 3.13). Installing Python 3.13.15 through WinGet and explicitly selecting that interpreter allowed `uv sync` to resolve and install the project successfully.

## What this establishes

The package builds, installs, and its two CLI paths completed against the public endpoints in this run. It verifies connectivity and the observed response shape for this capture only. It does not establish feed continuity, queue position, fill probability, trading performance, or profitability. The capture timestamps and payload hash are local research metadata, not an exchange signature.
