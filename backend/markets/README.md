# Markets

This folder is for **future** logic to integrate and process markets from feeds. The current priority is **not** feed integration.

## Current priority: Market Types UI (design from PDF)

- **First** deliverable is the **Market Types** admin screen that copies the design from **QNX Admin Manual - Market Types.pdf** (filters, table with all columns, “+ create Market Type” form, buttons, actions). See **`docs/MARKET_TYPES_QNX.md`** for the full spec (rows, buttons, filters as in the document).
- That screen is built **slowly**: we don’t have data from all feeds yet, and there are additional things to add before we can create any market. The UI can start with static/empty or minimal data.
- Feed integration and processing (parsing bwin/bet365/etc. into domain markets) will be added **later**, once the Market Types page exists and prerequisites are in place.

## What’s in this folder (for later)

- **`models.py`**, **`config.py`**, **`integration/`**, **`processor.py`** — Intended for future use: per-feed adapters, normalized market model, and processing pipeline. Not required for the Market Types UI. Use when we’re ready to wire real feed data and create markets from feeds.

## Summary

1. **Design first:** Implement the Market Types page to match the PDF (see `docs/MARKET_TYPES_QNX.md`).
2. **Build slowly:** Add data and behaviour step by step; no need for full feed data or market creation until the rest is ready.
3. **Feed logic later:** This folder will hold integration and processing when we add it.
