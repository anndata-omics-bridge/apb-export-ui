import assert from 'node:assert/strict'
import test from 'node:test'
import { render } from '@lit-labs/ssr'
import { ApbUploadForm, lacking } from '../src/upload-form.ts'
import type { Example, Output } from '../src/api.ts'

function output (title: string, levels: string[]): Output {
  return {
    id: `apb-export:${title}`, label: title, command: 'apb-export', name: title, extension: '.txt',
    annotation: true, fasta: true, levels,
    about: { title, file: '.txt', what: '', open: '', version: null, links: [], group: 'tool' }
  }
}

test('an example without the protein level cannot give a protein-level output', () => {
  assert.equal(
    lacking(output('Perseus', ['protein']), ['peptidoform_ion']),
    'Perseus reads protein; this example holds peptidoform_ion.'
  )
})

test('one level the output reads is enough', () => {
  assert.equal(lacking(output('QFeatures', ['peptidoform_ion', 'peptide', 'protein']), ['peptidoform_ion']), null)
})

test('APB2 formats and unread examples are never refused', () => {
  assert.equal(lacking(output('Parquet', []), ['peptidoform_ion']), null)
  assert.equal(lacking(output('Perseus', ['protein']), null), null)
})

const example: Example = {
  id: 'ex1', label: 'Tool', software: 'Tool', version: null, module: 'module', data: ['report.tsv'],
  stored_data: ['report.tsv'], folder: false, folder_files: [], params: 'params.json', stored_params: 'params.json',
  annotation: null, fasta: null, export: null, bytes: 10, levels: ['peptidoform_ion']
}

function form (): ApbUploadForm {
  const component = new ApbUploadForm()
  component.options = {
    software: ['Tool'],
    hints: { source: '', annotation: '', software: { Tool: { exports: [], params_required: true } } },
    outputs: [output('Perseus', ['protein'])],
    max_upload_bytes: 1,
    viewers: {},
    versions: {}
  }
  component.examples = [example]
  component.software = 'Tool'
  component.example = example
  return component
}

test('a greyed-out output says why on the tile, not only on hover', () => {
  const markup = Array.from(render(form().render())).join('')
  assert.match(markup, /class="tile-reason">(?:<!--[^>]*-->)*Perseus reads protein; this example holds peptidoform_ion\./)
})

test('a greyed-out example variant says why beside its buttons', () => {
  const markup = Array.from(render(form().render())).join('')
  assert.match(markup, /class="note reason">(?:<!--[^>]*-->)*Result file only: Tool needs its parameter file/)
  assert.match(markup, /class="note reason">(?:<!--[^>]*-->)*\+ parameters \+ annotation: this example has no sample annotation/)
})
