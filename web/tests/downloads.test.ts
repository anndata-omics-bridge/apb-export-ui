import assert from 'node:assert/strict'
import test from 'node:test'
import { render } from '@lit-labs/ssr'
import { ApbDownloads } from '../src/downloads.ts'
import type { Status } from '../src/api.ts'

function content (status: Status): string {
  const component = new ApbDownloads()
  component.status = status
  return Array.from(render(component.render())).join('')
}

const completed: Status = {
  id: 'job123', state: 'done', steps: [], error: null,
  files: [{ name: 'pmultiqc_report.html', bytes: 1000 }, { name: 'qpx.zip', bytes: 500 }]
}

test('completed report opens in a separate tab and remains downloadable', () => {
  const markup = content(completed)
  assert.match(markup, /href="api\/jobs\/job123\/report" target="_blank" rel="noopener"/)
  assert.match(markup, /Open pMultiQC report/)
  assert.match(markup, /download="pmultiqc_report.html"/)
  assert.match(markup, /download="qpx.zip"/)
})

test('ordinary exports show downloads without a report link', () => {
  const markup = content({ ...completed, files: [{ name: 'result.h5ad', bytes: 200 }] })
  assert.doesNotMatch(markup, /Open pMultiQC report/)
  assert.match(markup, /download="result.h5ad"/)
})

test('unfinished or failed jobs never expose a report link', () => {
  for (const state of ['queued', 'running', 'failed'] as const) {
    assert.doesNotMatch(content({ ...completed, state }), /Open pMultiQC report/)
  }
})
