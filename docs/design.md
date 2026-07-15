# askdocs - Design

Covers the minimal single-page web UI (Phase 4) and the API response design. The UI is deliberately small: one page with three regions - documents, ask, and answer. No framework; plain HTML + CSS + a single `app.js`. It is served as static files from `web/` by the FastAPI app.

## Design goals

- One screen, no navigation. A first-time user can upload a file and ask a question without instruction.
- Every asynchronous action has a visible state: idle, loading, success, empty, error.
- Fully usable by keyboard and screen reader. No color-only signaling.
- No build step, no external CDN assets, no web fonts. System font stack.

## Layout

Single centered column, max width `720px`, generous vertical rhythm. Three stacked cards:

1. **Documents card** - upload control plus the list of indexed documents (filename, chunk count, delete button).
2. **Ask card** - a labeled multiline question input and an "Ask" button.
3. **Answer card** - the answer text and a row of citation chips. Hidden until the first question is asked.

On narrow viewports (< 640px) the cards remain full-width with reduced padding. The column never exceeds the viewport width; long words and code wrap.

## Color and theme

Support light and dark via `prefers-color-scheme`. Use CSS custom properties so both themes share one stylesheet.

Light:
- `--bg: #f7f7f8`
- `--surface: #ffffff`
- `--text: #1a1a1a`
- `--muted: #5c5c66`
- `--border: #e0e0e6`
- `--accent: #2f5fe0` (buttons, focus ring, chips)
- `--accent-text: #ffffff`
- `--danger: #b3261e` (delete, error)
- `--success: #1b7f4b`

Dark:
- `--bg: #16161a`
- `--surface: #1f1f26`
- `--text: #f2f2f4`
- `--muted: #a0a0aa`
- `--border: #33333c`
- `--accent: #6b93ff`
- `--accent-text: #0f0f14`
- `--danger: #ff6b61`
- `--success: #56c98a`

Contrast: body text against surface, and button text against accent, must meet WCAG AA (>= 4.5:1 for normal text, >= 3:1 for large text and UI borders). Verify the accent/accent-text pair in both themes.

## Type scale

System font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`. Base `16px`, line-height `1.5`.

- Page title (`h1`): `1.5rem`, semibold
- Card heading (`h2`): `1.125rem`, semibold
- Body / answer text: `1rem`
- Muted metadata (chunk counts, timestamps): `0.875rem`, `--muted`
- Citation chip / snippet: `0.8125rem`

## Spacing

- Base unit `8px`. Card padding `24px`, gap between cards `16px`, gap between form controls `12px`.
- Buttons: `10px 16px` padding, `6px` radius. Inputs: `10px 12px`, `6px` radius, `1px solid var(--border)`.
- Citation chips: `4px 10px`, pill radius `999px`, `8px` gap between chips.

## Components and states

### Upload control
- Idle: a labeled file input (`<input type="file" accept=".txt,.md,.pdf">`) and an "Upload" button.
- Loading: button shows a spinner and text "Uploading...", the input and button are disabled, `aria-busy="true"` on the card.
- Success: the new document appears at the top of the documents list; a brief inline confirmation ("Indexed filename.txt - N chunks") with `role="status"`.
- Error: an inline error message below the control with `role="alert"`, using `--danger`, stating the reason (unsupported type, too large, extraction failed). The control returns to idle and remains usable.

### Documents list
- Populated: one row per document - filename, muted chunk count, and a "Delete" button. Delete shows a confirm step (native `confirm()` is acceptable) then a per-row loading state.
- Empty: a muted line "No documents yet. Upload one to get started."

### Ask input and button
- Idle: labeled `<textarea>` and an "Ask" button. Button disabled while the textarea is empty (also validated on submit).
- Loading: button shows "Thinking..." with a spinner, input disabled, `aria-busy="true"` on the answer card.
- Empty question submitted: inline validation message ("Enter a question."), no request sent.
- No documents indexed: if the user asks with an empty corpus, show the friendly "No documents indexed yet" message returned by the API in the answer card, not an error style.

### Answer card
- Loading: a skeleton or "Thinking..." placeholder with `aria-busy`.
- Success: the answer text, then a "Sources" label and citation chips.
- Error: a `role="alert"` message with the API error message.

### Citation chips
- Each chip shows the source filename and passage index, e.g. `notes.md #3`.
- A chip is a `<button>`; activating it expands (or scrolls to) a small panel showing the cited snippet text. Chips are keyboard-focusable and operable with Enter/Space.
- Chips use `--accent` background with `--accent-text`; the snippet panel uses `--surface` with a `--border`.

## Accessibility

- Every input has an associated `<label for>`. The file input, the question textarea, and buttons are all labeled.
- Focus is always visible: a `2px` `--accent` outline with offset on every interactive element. Do not remove default outlines without replacing them.
- Logical tab order top to bottom: upload, documents (with per-row delete), question, ask, then answer/chips once present.
- Status regions: upload confirmation and answer use `role="status"` / `aria-live="polite"`; errors use `role="alert"` / `aria-live="assertive"`.
- Loading states set `aria-busy` on the relevant card so assistive tech announces progress.
- Color is never the only signal: errors have text and an icon/prefix, success has text, disabled states use both reduced opacity and the `disabled` attribute.
- Contrast meets WCAG AA in both themes (see Color and theme).
- The page is operable with keyboard only, and remains usable at 200% browser zoom without horizontal scrolling of the body.

## API response design

The UI consumes the same JSON contract defined in `docs/api-contracts.md`. Design notes that shape the UI:

- **Answer response** is `{ "answer": string, "citations": Citation[] }`. `answer` is plain text; render it as text (preserve line breaks), do not render as HTML. `citations` may be empty (e.g. when the answer is "not found in the documents"); the UI hides the Sources row when empty.
- **Citation** is `{ "document_id", "filename", "chunk_index", "snippet", "score" }`. The chip label is built from `filename` + `chunk_index`; `snippet` fills the expandable panel; `score` is available for optional ordering but is not shown by default.
- **Empty-corpus** answers still return `200` with a friendly `answer` and empty `citations`; the UI shows them in the normal answer style, not as an error.
- **Errors** always arrive as `{ "error": { "code", "message" } }` with a non-2xx status. The UI shows `error.message` verbatim in the relevant `role="alert"` region and keys any special handling (e.g. re-prompting for an API key on `unauthorized`) off `error.code`.
- **Upload result** is `{ "id", "filename", "num_chunks", "status" }`; the UI uses `filename` and `num_chunks` for the confirmation and prepends the row to the list.
