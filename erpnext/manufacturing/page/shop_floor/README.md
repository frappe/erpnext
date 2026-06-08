# Shop Floor — User Guide

The **Shop Floor** is a touch‑ and keyboard‑friendly screen for running production
on the factory floor. It gives supervisors a live board of all work orders and gives
machine operators a focused screen to start, pause, complete and submit their jobs —
without ever opening a Work Order or Job Card form.

It is designed so that a non‑technical operator standing at a terminal can run the
whole shift from the keyboard (or a touch screen), and a supervisor can see at a glance
what is happening across every machine.

---

## 1. Opening the Shop Floor

1. Search for **Shop Floor** in the awesomebar, or go to **Manufacturing → Shop Floor**.
2. The screen opens at `/app/shop-floor`.

**Who sees what** depends on your role:

| Role | What you get |
| --- | --- |
| Shop Floor Manager, Manufacturing Manager, System Manager | The full **Board** (manager view) plus the ability to switch to the Operator view |
| Manufacturing User, Shop Floor User | The **Operator** view only |

Managers can flip between the two views at any time (see [View toggle](#23-switching-views)).

---

## 2. The Manager Board

The board is a paginated, colour‑coded grid of every work order, grouped into three
tabs. Use it to monitor the floor and to drill into any work order.

### 2.1 The three tabs

At the top‑left you'll see three tabs, each with a live count:

- 🟠 **In Progress** — work orders that have a job running right now.
- 🔵 **Pending** — work orders that are scheduled but not yet started.
- 🟢 **Completed** — finished work orders.

Click a tab (or press **1 / 2 / 3**) to switch between them.

### 2.2 Reading a work order card

Each card shows:

- **Workstation image** (a square photo of the machine; if none is set, the machine's
  initials are shown instead).
- **Work order title** and the **workstation / machine name** (with a 🏭 icon).
- An **operations progress bar** that fills as operations are finished:
  - 🟩 **Green** = operations completed
  - 🟧 **Orange** = operations in progress
  - ⬜ **Grey** = operations still pending
- A **status pill** and the **work order ID**.

> **Tip:** Click anywhere on a card (or focus it and press **Enter**) to open its job
> cards in the detail pane on the right.

### 2.3 Switching views

If you are a manager, a small **Board / Operator** toggle appears in the top‑left.
Click it, or press **`g`** then **`m`** (board) or **`o`** (operator), to switch.

### 2.4 Searching and filtering

- **Search box** (top‑centre): type any part of a work order name or item to filter the
  board. Press **`/`** to jump straight into the search box.
- **"With job cards only" checkbox**: ON by default. It hides work orders that have no
  job cards yet, so the board only shows things you can actually act on. Uncheck it to
  see every work order.

### 2.5 Loading more

Each tab loads 20 work orders at a time. Scroll to the bottom and click **Load more**
to fetch the next page. The footer shows how many of the total are loaded
(e.g. *Showing all 23*).

### 2.6 Opening a work order

Click a card to open its **detail pane** on the right. The detail pane is the operator
view scoped to that one work order, so you can start/run/complete its job cards directly,
and it lists the job cards **in operation sequence** — including completed ones — so you
can see the whole routing top to bottom.

---

## 3. The Operator View

This is the screen an operator uses for their machine or work order. Pick **either** a
**Machine** or a **Work Order** from the two filters in the top bar:

- **Machine filter** — shows every job queued at that workstation (respecting the
  machine's capacity, i.e. how many jobs it can run at once).
- **Work Order filter** — shows every job card for that one work order, in sequence.

At the top you get a quick **summary strip**: how many jobs are **Active** (and the
machine capacity, e.g. *1/2*), how many are **Pending / In Queue**, and how many are
**Completed**.

The screen is then divided into sections, top to bottom.

### 3.1 Active job slot

The job currently running (or the next one ready to start) sits at the top with a large,
clear card showing the item image, status, job card ID, operation, quantity and a **live
timer**. Its actions are:

| Button | What it does |
| --- | --- |
| **Start Job →** | Opens the *Start Job* dialog (start time + employees), then starts the timer |
| **Pause** | Pauses the running job and the timer |
| **Resume Job** | Resumes a paused job |
| **End Session** | Opens the *End Session* dialog to record the produced quantity and finish the session |
| **Transfer Materials** | Transfers the required raw materials for the job (see [Materials](#34-materials-panel)) |

### 3.2 Starting a job

1. Click **Start Job** (or press **`s`** on the focused card).
2. In the dialog, confirm the **Start Time** and add the **Employees** doing the job.
3. Press **Enter** or click **Start**. The timer begins.

> Everything in the dialog is keyboard‑operable — just press **Enter** to confirm.

### 3.3 Ending a session (recording output)

1. Click **End Session** (or press **`e`**).
2. Enter the **Completed Quantity** (and optionally **Process Loss Quantity**) and the
   **End Time**.
3. Choose:
   - **Save & Continue** — saves your numbers but keeps the job card open (e.g. if you'll
     produce more later), or
   - **Submit** — finalises the job card.
4. After submitting, you'll be asked whether to **Make a Manufacture Entry** (a stock
   entry for the finished goods). Click **Make Manufacture Entry** to create it, or
   **Skip**.

### 3.4 Materials panel

Under each job card is a collapsible **Materials** panel. Click it to expand and see each
required raw material with its status:

- 🟢 **Ready** — fully transferred and available
- **Available** — on hand at the source but not yet transferred
- 🔴 **Short** — not enough stock

Use **Transfer Materials** (in the panel or on the card) to move the raw materials to the
work‑in‑progress warehouse. Press **`t`** as a shortcut.

### 3.5 Up Next

Below the active slot, **Up Next** lists the pending job cards in queue. Each row shows
its status, item, quantity, and whether its **Materials** are **Ready** or **Awaiting
Transfer**. Use the **Start** or **Transfer** buttons on the row to act without leaving
the screen.

### 3.6 Ready to Submit

Any draft job cards that have a recorded quantity but haven't been submitted appear in
**Ready to Submit**, each with a **Submit** button. This is your safety net so finished
work isn't left un‑submitted.

### 3.7 Completed Operations / Today's Sessions

- **Completed Operations** (work‑order mode) lists the submitted job cards for the work
  order in operation sequence, so you can see the full routing and what's done.
- **Today's Sessions** (machine mode) lists what was submitted today, with the produced
  quantity, any process loss, and the session **duration**.

---

## 4. The Top Bar

The buttons on the top‑right are always available:

| Button | Shortcut | Action |
| --- | --- | --- |
| 🏠 **Home** | — | Go back to the Desk home page |
| 🔄 **Refresh** | **`r`** | Reload the current view with the latest data |
| 🔳 **Scan Job Card** | **`b`** | Open the barcode scanner |
| **?** | **`?`** | Open the keyboard‑shortcuts cheat sheet |

### 4.1 Scanning a job card

Click the **Scan** button (or press **`b`**) and scan a job card barcode. Most barcode
scanners send an **Enter** after the code, which automatically confirms — so you can scan
hands‑free and jump straight to that job.

---

## 5. Keyboard Shortcuts

The entire Shop Floor is built to run from the keyboard — the mouse is optional. Press
**`?`** at any time to see this cheat sheet on screen.

| Key | Action |
| --- | --- |
| `?` | Show the keyboard‑shortcut help |
| `/` | Jump to the search box |
| `r` | Refresh |
| `b` | Scan a job card |
| `g` then `m` / `o` | Switch between Board and Operator view |
| `1` / `2` / `3` | Switch board tab (In Progress / Pending / Completed) |
| `↑` / `↓`  (or `j` / `k`) | Move the selection up/down |
| `Enter` | Open the focused work order **or** run the primary action |
| `Esc` | Close the detail pane / leave the search box |
| `s` | **Start** or **Resume** the focused job |
| `p` | **Pause** or **Resume** the focused job |
| `e` | **End Session** for the active job |
| `t` | **Transfer Materials** |
| `Shift + S` | **Submit** the focused job card |

**In any dialog**, just press **Enter** to confirm the primary action (Start, Submit,
etc.). Enter is left alone inside multi‑line text boxes and while an autocomplete
dropdown is open, so you can still pick a value first.

---

## 6. A Typical Operator Flow

1. Open the Shop Floor and select your **Machine** (or **Work Order**).
2. The next job appears in the active slot. Press **`t`** to transfer materials if they
   aren't ready.
3. Press **`s`** to start → confirm employees → **Enter**. The timer runs.
4. Work the job. Press **`p`** to pause for a break, **`s`** to resume.
5. When done, press **`e`** → enter the completed quantity → **Enter** to submit.
6. Choose **Make Manufacture Entry** (or Skip).
7. The next job moves into the active slot — repeat.

---

## 7. A Typical Manager Flow

1. Open the Shop Floor (Board view).
2. Watch the **In Progress** tab — green/orange/grey bars show how far each work order has
   progressed through its operations.
3. Use **search** (`/`) or the tabs (`1` / `2` / `3`) to find a work order.
4. Click a card to open its job cards in sequence and, if needed, start/pause/submit on an
   operator's behalf.
5. Switch to **Pending** to see what's scheduled, and **Completed** to confirm finished
   work.
