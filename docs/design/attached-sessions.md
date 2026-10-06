# Attached sessions — connecting a learner's Claude or ChatGPT to AI Room (design, 2026-10-06)

## Why

Our lessons send learners out to claude.ai or ChatGPT ("Открываем claude.ai, новый чат…"). The practice happens there; AI Room only sees whatever gets pasted back. If the learner's own AI is connected, the chat where they actually work can do four things:
- **Know the current lesson.** It sees the section they're on, the task and the checklist, and coaches them through it.
- **Save the result back.** "Сохрани как результат урока" puts the work into Мои работы, which closes the loop.
- **Review the work.** It can check the work against the lesson's checklist. The learner's own subscription does the work, so AI Room needs no provider credentials or spend (handoff gap 7). The review is labelled as coming from their assistant, not as a verified review.
- **Answer "what next?"** It uses the same logic as `/continue`, and can show the learner's plan.

This also adds a return trigger: AI Room is present wherever the learner already spends time.

## Base scheme, adapted

Taken from Loopyard's session attach (the scheme, not the implementation):

1. **A logged-in learner issues a one-time, short-lived code.** It's stored only as a hash, bound to the learner, and expires in 10 minutes.
2. **The client exchanges the code, once, for a longer-lived credential.** The credential is scoped to that learner (default 30 days) and stored as a hash. The exchange is atomic: in SQLite, an `UPDATE … WHERE consumed_at IS NULL` replaces Loopyard's file lock. A second use returns 409; an expired code returns 410.
3. **Every later call presents the credential and nothing else.** A restricted tool set is pinned to that learner. The credential never grants web-session access.
4. **The learner sees and revokes connections** under "Подключения" in Моё обучение: the client's name, when it was created, when it was last used, and "Отключить".

How the credential is delivered depends on what each client supports (checked 2026-10-06):

| Client | How it connects | What that means for us |
|---|---|---|
| claude.ai, Claude Desktop and mobile (custom connectors) | OAuth 2.1 + PKCE, with client registration by DCR or CIMD. A bearer token pasted by the user isn't supported. ([Claude docs](https://claude.com/docs/connectors/building/authentication)) | **OAuth authorization-code flow.** The authorization code *is* the one-time code, and the consent page is AI Room's "Разрешить доступ к обучению?". |
| ChatGPT (developer mode / apps) | OAuth (DCR/CIMD) or no auth; private connectors expect OAuth. ([OpenAI docs](https://developers.openai.com/api/docs/guides/developer-mode.md)) | The same OAuth server. |
| Claude Code, Codex and other agent CLIs | Can fetch a URL and add an MCP server with an `Authorization` header. | **An attach link, Loopyard-style.** The agent fetches `/attach/<code>` once and gets templated instructions (`claude mcp add --transport http airoom https://…/mcp --header "Authorization: Bearer …"`). A HEAD request or a link-preview fetch doesn't consume the link. |

Both paths issue the same kind of credential, which is stored in one `connected_sessions` table and listed and revoked in the same place.

## Tools exposed (MCP, Streamable HTTP, stateless JSON)

| Tool | Does | Notes |
|---|---|---|
| `learning_status` | Current lesson and section, plan, next session, what's in progress. | Read-only. |
| `get_lesson(id?)` | Lesson text, sections, task, checklist, prompts; defaults to the current lesson. | **Same access rules as the web**, checked on every call (club lessons for members only; a revoked account loses access at once). Rate-limited. |
| `next_step` | The `/continue` logic. | Read-only. |
| `save_practice(lesson, body, status)` | Saves to Мои работы, marked as coming from the connected client. | Same validation and size limits as the web endpoint. |
| `mark_section(lesson, n)` | Records a section reached. | — |
| `review_checklist(lesson)` | Returns the checklist and the saved work, so the learner's AI can review it in the chat. | No verdict is stored as "verified". |

**Not exposed:** account, email, plan changes, membership, help tickets, other learners, anything editorial. Decided 2026-10-06: the assistant may save practice and mark sections; completing a lesson stays a click in AI Room.

## Safety and honesty

- **Codes and credentials:** hashed at rest, scoped, expiring and revocable; CSRF-protected consent; no tokens in URLs except the one-time attach code.
- **Paid content:** a member's AI sees what the member can already read; requests are rate-limited per credential. A free learner's AI gets the paywall outline only.
- **Writes:** only the learner's own practice and progress, all idempotent.
- **Prompt injection:** lesson text is first-party, and learner work is their own. Tool descriptions describe learning tasks only and never tell the AI to act outside them.
- **Copy:** the UI never presents the connected AI's feedback as AI Room's assessment.
- **Events:** `session_connected`, and `practice_saved` tagged with its source, so we can measure whether connecting helps return rates.

## Phasing

_Status 2026-10-06:_
- _Phase 1 is built: a copy-prompt fallback (`web/src/components/AssistantHandoff.tsx`)._
- _Phase 2 is built (`club/attach.py`). The owner asked for the link to run the other way, "a link I paste to Claude". So the lesson's main action is now **Скопировать ссылку для ассистента**, a one-time link the learner pastes into any assistant. It works with claude.ai and ChatGPT as long as they can open links and the address is public, as well as with Claude Code and other agents. A consumer chat reads the lesson from the document; an agent that can make HTTP requests or use MCP can also save work back. The text prompt is the fallback for apps that can't open links._
- _Phase 3, OAuth for claude.ai and ChatGPT connectors, is still to do._

| Phase | What | Effort |
|---|---|---|
| 1 | **"Продолжить в Claude / ChatGPT"** on the lesson: copies a ready prompt (lesson, current section, task, checklist, the learner's draft) and opens a new chat. Results are pasted back. No integration and nothing to secure. | S |
| 2 | The MCP endpoint and tool set, plus the attach link for agent CLIs. It can be tested locally with Claude Code, and it settles the tool design. | M |
| 3 | An OAuth 2.1 server (PKCE, DCR/CIMD, metadata documents, consent page) for claude.ai and ChatGPT, our main audience. It needs the public HTTPS staging host to test. | L |
