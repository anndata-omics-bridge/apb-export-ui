import assert from 'node:assert/strict'
import test from 'node:test'
import { render } from '@lit-labs/ssr'
import { anndataSidecars, structureViews, validatedRepresentation } from '../src/representation.ts'
import type { Level, Representation } from '../src/representation.ts'
import { ApbResultView } from '../src/result-view.ts'
import { ApbStructurePanel } from '../src/structure-panel.ts'
import type { Qc } from '../src/api.ts'

// A synthetic sidecar: two levels, peptide written before protein, one annotation table.
function level (name: string): Level {
  return {
    name,
    dimensions: { observations: 2, variables: 3 },
    obs: { row_count: 2, key_columns: ['sample'], columns: [{ name: 'sample', dtype: 'String' }] },
    var: { row_count: 3, key_columns: [name], columns: [{ name, dtype: 'String', null_count: 1 }] },
    layers: [
      { name: 'intensity', role: 'measurement', storage_slot: 'X', shape: { observations: 2, variables: 3 }, value_kind: 'quantitative', dtype: 'Float64', statistics: { total_count: 6, finite_count: 4, null_count: 2, median: 12.5 } },
      { name: 'q_value', role: 'confidence', storage_slot: 'layers', shape: { observations: 2, variables: 3 }, value_kind: 'quantitative', dtype: 'Float64' }
    ],
    apb: { parse: { rule: 'example' } }
  }
}

function sidecar (format: 'h5ad' | 'h5mu'): Representation {
  return {
    format: 'apb2-result-representation',
    format_version: '7',
    artifact: { name: `result.${format}`, physical_format: format },
    root: { apb: { hierarchy: { identities: [['protein', 'protein_group'], ['peptide', 'stripped_sequence']] } } },
    levels: [level('peptide'), level('protein')],
    annotation_tables: [{ name: 'protein', row_count: 3, key_columns: ['protein_group'], columns: [{ name: 'protein_group', dtype: 'String' }] }],
    feature_relations: [{ name: 'peptide_protein', blocks: [{ source: 'peptide', target: 'protein', links: 4 }] }]
  }
}

test('only the AnnData results have their sidecar loaded', () => {
  assert.deepEqual(
    anndataSidecars(['r.h5mu', 'r.h5mu.apb.json', 'r_explorede_protein.h5ad.apb.json', 'r.parquet.apb.json', 'r.duckdb.apb.json', 'msstats.csv']),
    ['r.h5mu.apb.json', 'r_explorede_protein.h5ad.apb.json']
  )
})

test('a sidecar of another version is refused, not misread', () => {
  assert.throws(() => validatedRepresentation({ ...sidecar('h5mu'), format_version: '6' }), /Unsupported APB representation version: 6/)
  assert.throws(() => validatedRepresentation({ format: 'other' }), /Unsupported APB representation format: other/)
  assert.equal(validatedRepresentation(sidecar('h5mu')).levels.length, 2)
})

test('an H5MU gives its container, its levels in hierarchy order, then its annotation tables', () => {
  const views = structureViews(sidecar('h5mu'))
  assert.deepEqual(views.map(({ label }) => label), ['MuData container', 'AnnData · protein', 'AnnData · peptide', 'AnnData · annotation/protein'])
  const [container, protein] = views
  assert.equal(container.kind === 'mudata' && container.modalities.length, 3)
  assert.equal(protein.kind === 'anndata' && protein.objectPath, 'mdata.mod["protein"]')
})

test('an H5AD keeps its root part apart from the level part', () => {
  const [view] = structureViews({ ...sidecar('h5ad'), levels: [level('protein')] })
  assert.equal(view.kind, 'anndata')
  if (view.kind !== 'anndata') return
  assert.equal(view.unsKey, 'uns["protein"]["apb"]')
  assert.ok(view.rootUns?.hierarchy)
  assert.equal(view.diagram.x?.name, 'intensity')
  assert.deepEqual(view.diagram.layers.map(({ name }) => name), ['q_value'])
})

function markup (element: { render: () => unknown }): string {
  return Array.from(render(element.render())).join('')
}

test('the structure panel opens on the container and draws every AnnData slot of a level', () => {
  const panel = new ApbStructurePanel()
  panel.structures = [{ file: 'result.h5mu.apb.json', representation: sidecar('h5mu') }]
  const container = markup(panel)
  assert.match(container, /MuData container/)
  assert.match(container, /peptide_protein/)
  panel.selected = 1
  const protein = markup(panel)
  for (const slot of ['var', 'obsp', 'x', 'obs', 'obsm', 'layers', 'uns', 'varm', 'varp']) {
    assert.match(protein, new RegExp(`data-slot="${slot}"`))
  }
  assert.match(protein, /intensity · X/)
  assert.match(protein, /4 · 66\.7%/)
  assert.match(protein, /2 · 33\.3%/)
})

test('several results name their file on each tab', () => {
  const panel = new ApbStructurePanel()
  panel.structures = [
    { file: 'r_explorede_protein.h5ad.apb.json', representation: { ...sidecar('h5ad'), levels: [level('protein')] } },
    { file: 'r_explorede_peptide.h5ad.apb.json', representation: { ...sidecar('h5ad'), levels: [level('peptide')] } }
  ]
  const html = markup(panel)
  assert.match(html, /r_explorede_protein\.h5ad/)
  assert.match(html, /r_explorede_peptide\.h5ad/)
})

const qc: Qc = {
  matrices: [{
    file: 'result.h5mu', level: 'protein', layer: 'X', features: 3,
    samples: [], density: { x: [], series: [] }, cv: { grouping: 'all samples', x: [], series: [] }
  }]
}

test('a finished job opens on quality control, with the structure as the second tab', () => {
  const view = new ApbResultView()
  view.qc = qc
  view.structures = [{ file: 'result.h5mu.apb.json', representation: sidecar('h5mu') }]
  const html = markup(view)
  assert.match(html, /aria-selected="true" >(?:<!--[^>]*-->)*Quality control/)
  assert.match(html, /aria-selected="false" >(?:<!--[^>]*-->)*AnnData structure/)
  assert.match(html, /<apb-qc-panel/)
  view.view = 'structure'
  assert.match(markup(view), /<apb-structure-panel/)
  view.clear()
  assert.equal(view.view, 'qc')
})

test('a result with one view shows it alone, and one with none shows nothing', () => {
  const view = new ApbResultView()
  view.structures = [{ file: 'result.h5mu.apb.json', representation: sidecar('h5mu') }]
  const html = markup(view)
  assert.match(html, /<h2>(?:<!--[^>]*-->)*AnnData structure(?:<!--[^>]*-->)*<\/h2>/)
  assert.doesNotMatch(html, /role="tablist"/)
  assert.doesNotMatch(markup(new ApbResultView()), /<section/)
})
