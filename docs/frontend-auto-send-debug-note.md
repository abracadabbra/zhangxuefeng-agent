# Frontend Auto-Send Debug Note

> Date: 2026-06-27
> Scope: `frontend`
> Topic: refresh -> refill form -> enter chat should auto-send exactly once

---

## Symptom

In the web frontend, the user reported two inconsistent behaviors around the initial auto-send flow:

1. After a hard refresh, completing score / province / subject / family condition could enter the chat page, but sometimes there was no streamed reply.
2. After a normal refresh back to the homepage, completing the form again could enter the chat page, but no initial message was sent and no `/api/chat` request was triggered.

The intended behavior is:

- Completing the form and entering chat should auto-send exactly once.
- Restoring an existing chat session should not auto-send again.

---

## Root Cause

The original implementation let `ChatInterface` infer whether it should auto-send by checking a combination of state such as:

- `messages.length === 0`
- `historyLoaded`
- `isLoading`
- `userProfile` / fetched profile availability

This made the behavior sensitive to render timing and refresh order. After returning to the portal and completing the form again, the chat page could miss the narrow window where all inferred conditions lined up.

There was also a separate debugging trap during validation:

- a stale frontend dev server was still running on one port
- the newly fixed frontend started on another port
- manual verification could accidentally hit the old instance and make the fix appear ineffective

---

## Fix

The auto-send trigger was changed from implicit inference to an explicit one-shot signal.

### Files changed

- [frontend/src/App.tsx](/Users/shentao/IdeaProjects/zhangxuefeng-agent/frontend/src/App.tsx)
- [frontend/src/components/ChatInterface.tsx](/Users/shentao/IdeaProjects/zhangxuefeng-agent/frontend/src/components/ChatInterface.tsx)
- [frontend/src/components/__tests__/App.test.tsx](/Users/shentao/IdeaProjects/zhangxuefeng-agent/frontend/src/components/__tests__/App.test.tsx)
- [frontend/src/components/__tests__/ChatInterface.test.tsx](/Users/shentao/IdeaProjects/zhangxuefeng-agent/frontend/src/components/__tests__/ChatInterface.test.tsx)

### Implementation summary

In `App.tsx`:

- add `autoStartRequestId` state
- when form completion succeeds, generate a fresh one-shot request id
- pass that id into `ChatInterface`
- clear it after the chat page confirms it has handled the request

In `ChatInterface.tsx`:

- auto-send only when `autoStartRequestId` is present
- deduplicate by request id with `handledAutoStartRef`
- wait until history loading completes
- skip auto-send if the restored session already has messages
- resolve profile from form props first, then fallback profile fetch if needed
- send the initial message through the normal streaming `sendMessage(...)` path

This makes the behavior deterministic:

- new form completion -> auto-send once
- restored chat history -> do not auto-send

---

## Verification

### Automated tests

Run:

```bash
cd frontend
npm test -- --run src/components/__tests__/App.test.tsx src/components/__tests__/ChatInterface.test.tsx
```

Expected result:

- the refresh-to-portal-and-refill flow triggers `/api/chat`
- the restored-chat-session flow does not trigger `/api/chat`

### Manual verification path

Use this exact flow:

1. Open the current frontend dev server URL
2. Refresh to the portal
3. Choose the gaokao flow again
4. Fill score, province, subject, family condition
5. Enter chat
6. Confirm:
   - the first user message is inserted automatically
   - `/api/chat` is called
   - the assistant reply streams in

---

## Important Debugging Note

When running Vite locally, do not assume the frontend is still on the original port.

If the configured port is occupied, Vite may start on a different port, for example:

- old instance: `http://127.0.0.1:4173/`
- newly fixed instance: `http://127.0.0.1:4174/`

Before concluding that a frontend fix did not work, first confirm:

1. which port the current `npm run dev` process actually bound to
2. whether another stale frontend instance is still running
3. whether the browser tab is pointed at the latest instance

Useful checks:

```bash
lsof -nP -iTCP:4173 -sTCP:LISTEN
lsof -nP -iTCP:4174 -sTCP:LISTEN
```

If multiple frontend instances exist, manual testing can easily hit the wrong build and produce a false negative.

---

## Rule To Keep

For one-shot UI side effects that must happen after a form-to-page transition, prefer an explicit trigger from the parent view over inferred state combinations inside the destination component.
