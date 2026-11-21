import assert from 'node:assert/strict'
import test from 'node:test'
import { render } from '@lit-labs/ssr'
import { ApbJobStatus } from '../src/job-status.ts'

test('submission has progress before the server assigns a job', () => {
  const progress = new ApbJobStatus()
  progress.submitting = true
  const markup = Array.from(render(progress.render())).join('')
  assert.match(markup, /Submitting conversion/)
  assert.doesNotMatch(markup, /Job log/)
})

test('a rejected submission keeps its error visible without a job', () => {
  const progress = new ApbJobStatus()
  progress.error = 'upload refused: Result file is empty'
  const markup = Array.from(render(progress.render())).join('')
  assert.match(markup, /upload refused: Result file is empty/)
  assert.doesNotMatch(markup, /Submitting conversion|Job log/)
})

function markup (progress: ApbJobStatus): string {
  return Array.from(render(progress.render())).join('')
}

test('a running step shows a moving bar and how long it has run', () => {
  const progress = new ApbJobStatus()
  progress.now = 1_000_000_000
  progress.status = {
    id: 'job123', state: 'running', error: null, files: [],
    steps: [{ name: 'convert', state: 'running', seconds: null, started: 1_000_000 - 134 }]
  }
  const content = markup(progress)
  assert.match(content, /running · 2 min 14 s/)
  assert.match(content, /<progress aria-label="convert running"/)
})

test('finished steps keep their duration and no bar', () => {
  const progress = new ApbJobStatus()
  progress.status = {
    id: 'job123', state: 'done', error: null, files: [],
    steps: [{ name: 'convert', state: 'done', seconds: 1.5, started: 1_000_000 }]
  }
  const content = markup(progress)
  assert.match(content, /done · 1.5 s/)
  assert.doesNotMatch(content, /<progress/)
})
