# AI Guardrails — Finance Operations Copilot

The copilot is an **analysis assistant**, never an autonomous agent. It answers
business questions by translating them into **validated, read-only SQL**.

## Pipeline
```
question → LLM → SQL → VALIDATE → Postgres (read-only) → verified rows → LLM explanation
```

## Guardrails (enforced in `backend/ai/copilot.py`)
1. **Read-only** — connection uses a read-only role; no writes possible.
2. **SELECT-only** — generated SQL must start with `SELECT`.
3. **Forbidden keywords** — `INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE/
   GRANT/MERGE/EXEC` are blocked.
4. **Table allowlist** — only known analytics tables/views may appear in
   FROM/JOIN. Unknown tables rejected.
5. **No fabricated numbers** — all figures come from SQL/Python aggregation,
   never from the LLM. The LLM only explains returned rows.
6. **Human review for actions** — the copilot never initiates payments or
   changes; it only reports.
7. **Graceful fallback** — if no API key is configured, a rule-based stub
   answers the common portfolio questions without an LLM.

## Validation function
`validate_sql(sql) -> (ok, error)`. Regex-based checks for forbidden keywords
and a table allowlist parsed from FROM/JOIN clauses.

## Example
Q: "Which vendors have the highest outstanding payments?"
→ SQL against `v_vendor_invoices_inr` grouped by vendor, filtered to
  unmatched invoices, ordered by payable INR.
→ Returns verified rows + plain-English explanation.

## Notes for deployment
- Store `OPENAI_API_KEY` in `.env` (gitignored). Any OpenAI-compatible
  endpoint works via `OPENAI_BASE_URL`.
- Keep the model temperature at 0 for deterministic SQL.
