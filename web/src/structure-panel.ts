import { LitElement, html, nothing } from './lit.ts'
import type { TemplateResult } from './lit.ts'
import { matrixSummary, resultName, structureViews } from './representation.ts'
import type { AnnDataStructure, ApbMetadata, Layer, MuDataStructure, NamedTable, ResultStructure, StructureView, TableDescription } from './representation.ts'

// The AnnData slots of each result, from its APB2 sidecar. Ported from APB Studio's corpus
// viewer (render/anndata-structure.ts) to Lit templates.

const count = (value: number | null | undefined): string => (value ?? 0).toLocaleString()

function number (value: number | null): string {
  if (value === null) return '—'
  const absolute = Math.abs(value)
  if (absolute >= 1_000_000 || (absolute > 0 && absolute < 0.001)) return value.toExponential(3)
  return value.toLocaleString(undefined, { maximumFractionDigits: 4 })
}

function fraction (value: number | null, all: number | null): string {
  if (value === null) return '—'
  if (all === null || all === 0) return count(value)
  return `${count(value)} · ${(100 * value / all).toFixed(1)}%`
}

function list (items: string[], empty: string): TemplateResult {
  if (items.length === 0) return html`<p class="structure-empty">${empty}</p>`
  return html`<ul class="structure-list">${items.map(item => html`<li>${item}</li>`)}</ul>`
}

const columns = (description: Pick<TableDescription, 'columns'>): TemplateResult =>
  list(description.columns.map(({ name, dtype, null_count: nulls }) => `${name} · ${dtype}${nulls ? ` · ${count(nulls)} null` : ''}`), 'No columns')

function slot (name: string, title: string, summary: string, content: TemplateResult): TemplateResult {
  return html`
    <section class="structure-slot" data-slot=${name} aria-label=${title}>
      <header><h5>${title}</h5><span class="structure-summary">${summary}</span></header>
      ${content}
    </section>
  `
}

function facts (entries: Array<[string, string]>): TemplateResult {
  return html`<dl class="structure-facts">${entries.map(([label, value]) => html`<div><dt>${label}</dt><dd>${value || '—'}</dd></div>`)}</dl>`
}

function axis (name: 'obs' | 'var', description: TableDescription): TemplateResult {
  return slot(name, name, `${count(description.row_count)} rows · ${count(description.columns.length)} columns`, html`
    <p class="structure-index">${name}_names ← ${description.key_columns.join(', ') || 'none'}</p>
    ${columns(description)}
  `)
}

function matrix (layer: Layer, primary: boolean): TemplateResult {
  const summary = matrixSummary(layer)
  const entries: Array<[string, string]> = [
    ['Shape', `${count(summary.shape.observations)} × ${count(summary.shape.variables)}`],
    ['Dtype', summary.dtype],
    ['Kind', summary.kind],
    ['Finite', fraction(summary.finiteCount, summary.totalCount)],
    ['Missing', fraction(summary.missingCount, summary.totalCount)],
    ...(summary.infiniteCount ? [['Infinite', fraction(summary.infiniteCount, summary.totalCount)] as [string, string]] : []),
    ['Zeros', fraction(summary.zeroCount, summary.totalCount)],
    ['Mean', number(summary.mean)],
    ['Median', number(summary.median)],
    ['Range', summary.minimum === null && summary.maximum === null ? '—' : `${number(summary.minimum)} – ${number(summary.maximum)}`]
  ]
  return html`
    <section class="structure-card">
      <header><h6>${primary ? `${summary.name} · X` : summary.name}</h6><span class="structure-role">${primary ? 'primary' : summary.role}</span></header>
      ${facts(entries)}
    </section>
  `
}

function aligned (name: string, tables: NamedTable[]): TemplateResult {
  const cards = tables.map(table => {
    const cells = table.row_count * table.columns.length
    const nulls = table.columns.reduce((sum, column) => sum + (column.null_count ?? 0), 0)
    return html`
      <section class="structure-card">
        <header><h6>${table.name}</h6><span class="structure-shape">${count(table.row_count)} × ${count(table.columns.length)}</span></header>
        ${facts([
          ['Null cells', fraction(nulls, cells)],
          ['Dtypes', [...new Set(table.columns.map(({ dtype }) => dtype))].join(', ')],
          ['Keys', table.key_columns.join(', ') || 'none']
        ])}
        ${columns(table)}
      </section>
    `
  })
  return slot(name, name, `${count(tables.length)} objects`, tables.length > 0 ? html`<div class="structure-grid">${cards}</div>` : html`<p class="structure-empty">Empty</p>`)
}

interface UnsPart { uns: ApbMetadata, unsKey: string, hasStorage: boolean }

// One uns slot holding every APB part of an object: an H5AD has a root and a level part.
function uns (parts: UnsPart[], objectPath: string): TemplateResult {
  const children = parts.reduce((sum, part) => sum + Object.keys(part.uns).length, 0)
  const stored = parts.some(part => part.hasStorage)
  const title = parts.filter(part => Object.keys(part.uns).length > 0).map(part => part.unsKey).join(' · ') || 'uns'
  return slot('uns', title, stored ? `${count(children)} direct ${children === 1 ? 'child' : 'children'} · storage omitted` : 'Empty', html`
    ${parts.map(part => html`
      <div class="structure-uns">
        ${Object.entries(part.uns).map(([tool, value]) => html`
          <details>
            <summary><code>${objectPath}.${part.unsKey}[${JSON.stringify(tool)}]</code></summary>
            <pre>${JSON.stringify(value, null, 2)}</pre>
          </details>
        `)}
      </div>
      ${part.hasStorage ? html`<p class="structure-empty">Also stored: ${part.unsKey}["storage"], the physical reconstruction descriptor, not described by the sidecar.</p>` : nothing}
    `)}
    ${children === 0 && !stored ? html`<p class="structure-empty">Empty; an annotation AnnData has no APB metadata. Its provenance belongs to the MuData container.</p>` : nothing}
  `)
}

function anndata (view: AnnDataStructure): TemplateResult {
  const { diagram } = view
  const x = diagram.x
  return html`
    <section class="structure-object">
      <h4>${view.label} · ${count(diagram.dimensions.observations)} observations × ${count(diagram.dimensions.variables)} variables</h4>
      <code class="structure-path">${view.objectPath}</code>
      <div class="anndata-diagram" role="group" aria-label=${`${diagram.name} AnnData structure`}>
        ${axis('var', diagram.var)}
        ${aligned('obsp', diagram.aligned.obsp)}
        ${slot('x', 'X', x ? x.name : view.annotation ? 'None · annotation modality' : 'Missing primary layer',
          x ? matrix(x, true) : html`<p class="structure-empty">${view.annotation ? 'X = None; features are described in var.' : 'No primary matrix'}</p>`)}
        ${axis('obs', diagram.obs)}
        ${aligned('obsm', diagram.aligned.obsm)}
        ${slot('layers', 'layers', `${count(diagram.layers.length)} matrices`,
          diagram.layers.length > 0 ? html`<div class="structure-grid">${diagram.layers.map(layer => matrix(layer, false))}</div>` : html`<p class="structure-empty">No layers</p>`)}
        ${uns([
          ...(view.rootUns ? [{ uns: view.rootUns, unsKey: 'uns["apb"]', hasStorage: true }] : []),
          { uns: diagram.uns, unsKey: view.unsKey, hasStorage: view.hasStorage }
        ], view.objectPath)}
        ${aligned('varm', diagram.aligned.varm)}
        ${aligned('varp', diagram.aligned.varp)}
      </div>
    </section>
  `
}

function mudata (view: MuDataStructure): TemplateResult {
  return html`
    <section class="structure-object">
      <h4>MuData container</h4>
      <code class="structure-path">${view.objectPath}</code>
      <p class="note">Root metadata and cross-modality relations live here; each embedded AnnData has its own tab.</p>
      <table class="counts">
        <thead><tr><th>mod</th><th>Observations</th><th>Variables</th></tr></thead>
        <tbody>${view.modalities.map(({ name, dimensions }) => html`<tr><td>${name}</td><td>${count(dimensions.observations)}</td><td>${count(dimensions.variables)}</td></tr>`)}</tbody>
      </table>
      ${uns([{ uns: view.uns, unsKey: 'uns["apb"]', hasStorage: view.hasStorage }], view.objectPath)}
      ${slot('varp', 'varp · feature relations', `${count(view.relations.length)} relations`, view.relations.length > 0
        ? html`<table class="counts">
            <thead><tr><th>Relation</th><th>From</th><th>To</th><th>Links</th></tr></thead>
            <tbody>${view.relations.flatMap(relation => relation.blocks.map(block => html`<tr><td>${relation.name}</td><td>${block.source}</td><td>${block.target}</td><td>${count(block.links)}</td></tr>`))}</tbody>
          </table>`
        : html`<p class="structure-empty">No cross-modality feature relations.</p>`)}
    </section>
  `
}

interface Tab { file: string, view: StructureView }

// Every object of every result as one row of tabs; a job with several results, such as
// exploreDE's one file per level, names each tab's file.
export const structureTabs = (structures: ResultStructure[]): Tab[] =>
  structures.flatMap(({ file, representation }) => structureViews(representation).map(view => ({ file, view })))

export class ApbStructurePanel extends LitElement {
  static properties = {
    structures: { attribute: false },
    selected: { state: true }
  }

  structures: ResultStructure[] = []
  selected = 0

  createRenderRoot (): this { return this }

  render (): TemplateResult | typeof nothing {
    const tabs = structureTabs(this.structures)
    const several = this.structures.length > 1
    const current = Math.min(this.selected, tabs.length - 1)
    const chosen = tabs[current]
    if (chosen === undefined) return nothing
    return html`
      <section class="structure">
        ${tabs.length > 1
          ? html`<nav class="tabs" role="tablist" aria-label="AnnData objects">
              ${tabs.map(({ file, view }, index) => html`
                <button type="button" role="tab" aria-selected=${String(index === current)} @click=${() => { this.selected = index }}>
                  ${view.label}${several ? html` <span class="note">${resultName(file)}</span>` : nothing}
                </button>
              `)}
            </nav>`
          : nothing}
        <p class="note">${resultName(chosen.file)}, as described by its APB sidecar <code>${chosen.file}</code>.</p>
        ${chosen.view.kind === 'mudata' ? mudata(chosen.view) : anndata(chosen.view)}
      </section>
    `
  }
}
