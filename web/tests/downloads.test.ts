import assert from 'node:assert/strict'
import test from 'node:test'
import { render } from '@lit-labs/ssr'
import { ApbDownloads } from '../src/downloads.ts'
import type { Options, Status } from '../src/api.ts'

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

const explorede = {
  software: [],
  hints: { source: '', annotation: '', software: {} },
  max_upload_bytes: 0,
  versions: {},
  viewers: { exploreDE: 'https://shiny.example/app/exploreDE/' },
  outputs: [{
    id: 'apb-export:explorede',
    label: 'explorede (.h5ads)',
    command: 'apb-export',
    name: 'explorede',
    extension: '.h5ads',
    annotation: true,
    fasta: true,
    levels: ['protein', 'peptide', 'peptidoform_ion'],
    about: { group: 'tool', title: 'exploreDE', file: '.h5ad per level', what: '', open: '', version: '1.0', links: [], viewer: 'exploreDE' }
  }]
} satisfies Options

// The rendered text without Lit's template markers.
function viewed (files: Status['files']): string {
  const component = new ApbDownloads()
  component.status = { ...completed, files }
  component.options = explorede
  component.page = 'https://apps.example/apb-export/#job123'
  return Array.from(render(component.render())).join('').replace(/<!--[^>]*-->/g, '')
}

test('each exploreDE level opens exploreDE in a new tab with its file URL', () => {
  const markup = viewed([
    { name: 'report_explorede_precursor.h5ad', bytes: 900 },
    { name: 'report_explorede_precursor.h5ad.apb.json', bytes: 90 },
    { name: 'report_explorede_protein.h5ad', bytes: 800 }
  ])
  for (const level of ['precursor', 'protein']) {
    const file = encodeURIComponent(`https://apps.example/apb-export/api/jobs/job123/files/report_explorede_${level}.h5ad`)
    assert.ok(markup.includes(`href="https://shiny.example/app/exploreDE/?data=${file}" target="_blank" rel="noopener">Open ${level} in exploreDE</a>`))
  }
  assert.equal(markup.match(/in exploreDE</g)?.length, 2, 'no link for the sidecar')
  assert.match(markup, /download="report_explorede_protein.h5ad"/)
})

test('other h5ad results get no exploreDE link', () => {
  assert.doesNotMatch(viewed([{ name: 'report_proteopy.h5ad', bytes: 900 }]), /in exploreDE/)
})
