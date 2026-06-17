import { expect, test as base, type Route } from '@playwright/test'

const jsonResponse = (body: unknown) => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify(body),
})

const emptySseResponse = {
  status: 200,
  headers: {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache',
  },
  body: 'data: {"type":"text","content":""}\n\n',
}

async function fulfillDefaultApi(route: Route) {
  const request = route.request()
  const url = new URL(request.url())
  const path = url.pathname

  if (path === '/api/sessions') {
    return route.fulfill(jsonResponse([]))
  }

  if (/^\/api\/session\/[^/]+\/favorites$/.test(path)) {
    return route.fulfill(jsonResponse({ favorite_keys: [] }))
  }

  if (/^\/api\/session\/[^/]+\/export\/pdf$/.test(path)) {
    return route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="chat-e2e.pdf"',
      },
      body: '%PDF-1.4\n% e2e pdf export\n',
    })
  }

  if (/^\/api\/session\/[^/]+\/export$/.test(path)) {
    return route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/markdown; charset=utf-8',
        'Content-Disposition': 'attachment; filename=chat-e2e.md',
      },
      body: '# 张雪峰 AI 志愿建议报告\n\nE2E export fixture\n',
    })
  }

  if (/^\/api\/session\/[^/]+$/.test(path)) {
    return route.fulfill(jsonResponse(request.method() === 'GET' ? { messages: [] } : {}))
  }

  if (/^\/api\/profile\/[^/]+$/.test(path)) {
    return route.fulfill(jsonResponse({}))
  }

  if (path === '/api/chat') {
    return route.fulfill(emptySseResponse)
  }

  if (path === '/api/recommend') {
    return route.fulfill(jsonResponse({ recommendations: [], summary: '', gradient_summary: {} }))
  }

  return route.fallback()
}

const test = base.extend({
  defaultApiMocks: [
    async ({ context }, use) => {
      await context.route('**/api/**', fulfillDefaultApi)
      await use(undefined)
      await context.unroute('**/api/**', fulfillDefaultApi)
    },
    { auto: true },
  ],
})

export { expect, test }
