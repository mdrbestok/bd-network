# BD Network – Product / Engineering TODO

Items below are for planning and prioritization. Not all are scoped or scheduled.

---

## Graph & UX

### Startup animation (deferred)
- **Goal:** On load, graph starts as a tight ball in the center, expands out to a readable layout, then a short “bounce” before settling.
- **Status:** Previously attempted; view kept going blank or staying tiny. Reverted to static start with one-time zoom-to-fit on engine stop.
- **Notes:** Would need reliable “follow” of the expanding graph (camera/zoom) and/or delayed zoom-to-fit so the ball phase is visible without blank screen.

### Trial node colors by status
- **Goal:** Visually distinguish trial status without extra UI.
- **Idea:** Use a lighter orange (or muted color) for trials that are **not recruiting** or **not active** (e.g. completed, terminated). Keep current orange for recruiting / active.
- **Touches:** `NetworkGraph` node rendering (`nodeCanvasObject`), possibly `lib/utils` node/edge styles.

---

## Data quality & curation

### Correct / approve assets and clinical sites
- **Goals:**
  - Allow users to **correct** asset or site (e.g. modality, targets, owner) and have that preserved.
  - Allow users to **approve** inferred data (e.g. “confirm this sponsor”) so it’s not overwritten by future syncs.
  - Support **adding new** assets and **adding new** clinical sites (companies) that aren’t yet in the graph.
- **Notes:** Asset edits and “user confirmed” ownership already exist; extend to sites and to “add new” flows.

### Link to press release for a deal
- **Goal:** In addition to ClinicalTrials.gov (and any other trial links), support a **link to a press release** (or news article) about a **specific deal** (e.g. licensing, acquisition).
- **Touches:** Deal model / API, detail drawer or deal-focused view, ingest if we ever pull deals from press.

---

## Deals (acquisitions, mergers, licensing)

### Model and data
- **Goal:** Represent **acquisitions, mergers, and licensing deals** (not only trials/assets).
- **Constraint:** Don’t show deals in the same dense view as the full trial/asset graph or it gets messy.
- **Idea:**
  - In a “deals-aware” view: show **assets** and **sponsors** (companies) plus a **list of deals** that apply to those companies (or to the current selection).
  - When user **multi-selects two sponsors**, show:
    - Existing shortest path / relationship info, and
    - **Deals between those two** (e.g. licensing deal A → B, acquisition B → A).
- **Data:** Deals have parties (companies), type (acquisition, merger, licensing, etc.), dates, and optionally link to press release / 10-K.

### Ingest from 10-K / 10-Q
- **Goal:** Ingest deal (and possibly relationship) info from **SEC 10-K / 10-Q**.
- **Options:**
  - **API:** Use an SEC or financial API that exposes filings and structured deal/event data.
  - **PDF link:** User provides a link to the PDF; system **downloads** and **reviews** (e.g. extract text, then parse or use LLM) to find acquisitions, mergers, licensing, partnerships.
- **Scope:** Define ingest pipeline (link or API → normalized deals + link to press release / filing), then plug into “deals between two sponsors” and deal list views.

---

## Summary checklist (for your own tracking)

- [ ] Startup animation (ball → expand → bounce) – deferred
- [ ] Trial node colors: lighter orange (or muted) for not recruiting / not active
- [ ] Correct / approve assets and clinical sites; add new assets and sites
- [ ] Link to press release (or article) per deal
- [ ] Deals model and UI: acquisitions, mergers, licensing; show with assets/sponsors and list of deals; multi-select two sponsors → show deals between them
- [ ] Ingest from 10-K / 10-Q (API or PDF link → download & review)

---

*Edit this file as you prioritize or complete items.*
