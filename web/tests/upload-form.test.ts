import assert from 'node:assert/strict'
import test from 'node:test'
import { lacking } from '../src/upload-form.ts'
import type { Output } from '../src/api.ts'

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
