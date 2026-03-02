# Feeder Configuration — design spec (from QNX Admin Manual)

**Source:** `docs/QNX Admin Manual - Feeder Configuration.pdf`  
**Goal:** Implement the Feeder Configuration screen that configures automation of the mapping process per feed, per sport/category/league, and (when a sport is selected) Feeder Incidents Configuration. Do not start implementation until the spec is double-checked.

---

## Purpose

Feeder Configuration is the part of the platform responsible for configuring the set-up of all available Feed/Feeders. The main purpose is to **enable automation of the mapping process** in different aspects and circumstances. Three top-level filters (Sport, Category, League) let the admin scope configuration to a specific sport, then category, then league.

---

## Top filters

Admin filters feeder configuration by sport, category, and league. All are **single-select** and **cascading**.

| Filter | Description |
|--------|-------------|
| **Sport** | Dropdown — choose which sport’s feeder configuration is shown below. Only one sport can be selected. List is dynamic (expands as new sports are added by feeder providers). |
| **Category** | Dropdown — choose which category (under the chosen sport) to filter by. **Requires Sport to be selected.** Only one category. List is dynamic (expands as new categories under that sport are mapped). |
| **League** | Dropdown — choose which league (under the chosen category) to filter by. **Requires Category to be selected.** Only one league. List is dynamic (expands as new leagues under that category/sport are mapped). |

---

## Configuration hierarchy and inheritance

- Configuration can be set at **Sport**, **Category**, or **League** level.
- **Display:** When a setting is overridden at a lower level, the higher-level value is shown in parentheses. Example: if "Automapping enabled" is "Yes" at Sport (Soccer) and "No" at Category (England), display: **"(Yes) No"**.
- **Scope of parent display:** Only **one level above** is shown — e.g. at Category you see Sport’s value in parentheses; at League you see Category’s value in parentheses.
- **Inheritance:** If a setting is **"Not set"** at the current level, the value from the level above applies. If the higher-level setting is also "Not set", the system treats the feeder configuration system action as **No** / disabled.

---

## Feeder configuration system actions

These settings control automation behaviour. Each can be applied at Sport / Category / League (depending on what is selected). Values: **Yes**, **No**, or **Not set** (inherit from above).

| Setting | Yes | No |
|---------|-----|-----|
| **Automapping enabled** | Enable automapping of events already mapped in the system (sport, category, league, teams) into already created events. | Disable that automapping. |
| **Automapping teams enabled** | Enable automapping of teams that are already mapped in the system. | Disable automapping of teams. |
| **Automapping start time threshold (in hours)** | Numeric setting: event start time threshold in hours. A new event (that can be automapped) may automap to an already created event only if the start time difference is not longer than this value. | — |
| **Auto live offer** | Enable the auto-live offer to be set by the feeder for the event. | Disable. |
| **Automap neutral grounds** | Enable automapping of events that are set as neutral ground in already created events. | Disable. |
| **Auto update start time rank** | Numeric/priority: admin sets priority between feeders. Feeders with a **higher** number have higher priority; the feeder with the higher number will auto-set the start time of the event when multiple feeders are mapped for the same event. | — |
| **Market mapping behavior** | **At Least One Active** — automap events with at least one active market in an already created event. **All Active** — automap only if all markets are active in that event. | — |
| **Auto create domain event** | Enable auto-create of events that are already mapped in the system. | Disable. |
| **Auto create domain player** | Enable auto-create of player/team that is not already mapped in the system. | Disable. |
| **Automap market type enabled** | Enable automapping of market types that are already mapped in the system. | Disable. |
| **Auto create market type enabled** | Enable creation of a market type that is not already mapped in the system. | Disable. |
| **Settlement enabled** | Enable auto-settlement of event markets by the feeder. | Disable. |
| **Resettlement enabled** | Enable auto-resettlement of event markets by the feeder. | Disable. |
| **Bet void enabled** | Enable auto-settlement to void the status of event markets by the feeder. | Disable. |
| **Bet void rollback enabled** | Enable auto void-status settlement rollback to initial settlement of event markets by the feeder. | Disable. |
| **Auto map one to many enabled** | Enable automapping of events already mapped in the system to already created events with the same opponents but different start times (same event). | Disable. |
| **External trading service enabled** | Enable external trading service. | Disable. |

---

## Feeder Incidents Configuration

**Visibility:** Shown only when a **Sport is selected**. It appears **at the bottom** of the Feeder Configuration page.

**Purpose:** Configure which incident/data types each feeder provides, per Sport (and optionally per Category or League of that sport). On top is a list of **Feeder providers**; for each of them, configuration for different system actions (incident types) can be set.

### Incident types (Yes/No per feed)

| Setting | Description |
|---------|-------------|
| **Score** | Load score data if the feeder provides it and setting is Yes. |
| **Time** | Load time data if the feeder provides it and setting is Yes. |
| **Live State** | Load live state if the feeder provides it and setting is Yes. |
| **Incidents** | Load incident data if the feeder provides it and setting is Yes. |
| **Stats** | Load stats data if the feeder provides it and setting is Yes. |
| **Podcast** | Load podcast data if the feeder provides it and setting is Yes. |
| **Weather** | Load weather data if the feeder provides it and setting is Yes. |
| **Pitch** | Load pitch information if the feeder provides it and setting is Yes. |
| **Surface** | Load surface information if the feeder provides it and setting is Yes. |
| **Video** | Load the video URL if the feeder provides it and setting is Yes. |

### Actions / buttons

| Element | Description |
|---------|-------------|
| **Sort** | Button — sort Feed Sources. A Feed Source placed higher is prioritized when the system receives the same data from 2 or more feed sources. |
| **Add "+"** | Button — add new Feed Source to the Feeder Incidents Configuration list. |
| **Switch** | Button — Enable/Disable a Feed Source. |
| **Edit** | Button — configure which data the Feed Source will provide. |
| **Save** | Button — save changes in Feeder Incidents Configuration. |
| **Cancel** | Button — cancel changes and close. |

---

## Implementation notes

- **Data:** Need a store for feeder configuration (e.g. per feed, per sport/category/league) and for feeder incidents configuration (per feed, per sport). Current `feeds.csv` only has domain_id, code, name; this spec implies many new fields or a separate config store.
- **Placement:** Configuration → **Feeder** in the menu (at the bottom of the Configuration dropdown), route e.g. `/feeders`.
- **Order of build:** Filters first (Sport → Category → League), then the main configuration grid/table with system actions, then Feeder Incidents Configuration section (visible when sport selected). Inheritance and "(Parent) Current" display can be added as the data model is defined.
- **Double-check:** Implementation must not start until this spec is reviewed and agreed.
