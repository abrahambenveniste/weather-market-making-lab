# Capture validation and normalization

**Status:** implemented and tested against synthetic edge cases and the first local public capture.

## Run

After at least one successful collection:

```shell
uv run weather-mm normalize
```

The command reads `data/raw/kalshi-public.jsonl`, verifies each payload hash, and writes:

- `data/derived/markets.csv` — one row per market in each market-list response;
- `data/derived/orderbook-levels.csv` — one row per captured bid price level and contract side.

Both outputs are local derived data and are excluded from Git. Re-running the command replaces the derived CSVs; it does not append duplicate rows. For alternate locations, use `--input`, `--markets-output`, and `--levels-output`.

## Validation and representation

Before writing each capture, the normalizer checks the record type, successful HTTP status, timezone-aware receive timestamp, response payload object, and SHA-256 of the canonical JSON payload. It rejects malformed JSON, unsupported payload shapes, invalid prices, non-positive level sizes, or an order-book endpoint from which it cannot identify a ticker. Error messages identify the capture line and field/level.

Prices and sizes remain decimal strings in CSV; they are not rounded through binary floating point. The order-book endpoint supplies YES bids and NO bids. The normalizer records those bid levels as returned. In a binary market, a bid on one contract implies the corresponding ask on the opposite contract at `1 - bid price`; no ask rows are fabricated in the output.

CSV output is staged in temporary files and replaces the previous files only after the full input validates. This avoids publishing a partially normalized run when a later capture line is corrupt. The two-file replacement is not a single filesystem transaction, so an operating-system failure between replacements could leave outputs from different runs; rerunning after resolving the error regenerates both.

## First local result

On the first capture file, validation accepted two capture records: one market-list page with 12 markets and one order-book snapshot with 49 levels total (1 YES bid level and 48 NO bid levels). A subsequent one-market discovery call added one more valid market-list record. Raw payloads remain local and ignored by Git.

## Limits

Hash validation detects accidental payload edits relative to the locally recorded hash. The hash is not signed by Kalshi and does not independently establish source authenticity. REST snapshots do not reveal intervening events or queue position; these CSVs are inputs for data inspection, not evidence of fill probability or profitability.

