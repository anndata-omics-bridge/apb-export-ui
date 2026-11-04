// The JSON sidecar APB2 writes beside every HDF5 result, `<result>.apb.json`, and its pure
// projections into AnnData slots. Ported from APB Studio's corpus viewer
// (apb_studio/viewer/src/corpus/representation.ts); this app stays independently locked.

export const REPRESENTATION_FORMAT = 'apb2-result-representation'
export const REPRESENTATION_VERSION = '7'
export const SIDECAR_SUFFIX = '.apb.json'
const EMBEDDED_JSON_FIELDS = new Set(['rule_json', 'plan_json'])

export interface Dimensions { observations: number, variables: number }
export interface TableColumn { name: string, dtype: string, null_count?: number }
export interface TableDescription { row_count: number, key_columns: string[], columns: TableColumn[] }
export interface NamedTable extends TableDescription { name: string }

export interface Statistics {
  total_count?: number
  finite_count?: number
  null_count?: number
  nan_count?: number
  positive_infinity_count?: number
  negative_infinity_count?: number
  zero_count?: number
  mean?: number | null
  median?: number | null
  minimum?: number | null
  maximum?: number | null
}

export interface Layer {
  name: string
  role: string
  primary?: boolean
  storage_slot?: 'X' | 'layers'
  shape: Dimensions
  value_kind: string
  dtype?: string
  unit?: string | number | boolean | null
  scale?: string | number | boolean | null
  statistics?: Statistics
}

export type AlignedSlot = 'obsm' | 'varm' | 'obsp' | 'varp'
export type ApbMetadata = Record<string, unknown> & { hierarchy?: { identities?: Array<[string, string]> } }

export interface Level {
  name: string
  dimensions: Dimensions
  obs: TableDescription
  var: TableDescription
  layers: Layer[]
  aligned?: Partial<Record<AlignedSlot, NamedTable[]>>
  apb?: ApbMetadata
}

export interface FeatureRelation {
  name: string
  blocks: Array<{ source: string, target: string, links: number }>
}

export interface Representation {
  format: typeof REPRESENTATION_FORMAT
  format_version: typeof REPRESENTATION_VERSION
  artifact: { name: string, physical_format: string } | null
  root?: { apb?: ApbMetadata } | null
  levels: Level[]
  annotation_tables?: NamedTable[]
  feature_relations?: FeatureRelation[]
}

export interface AnnDataDiagram {
  name: string
  dimensions: Dimensions
  x: Layer | null
  layers: Layer[]
  obs: TableDescription
  var: TableDescription
  aligned: Record<AlignedSlot, NamedTable[]>
  uns: ApbMetadata
}

export interface AnnDataStructure {
  kind: 'anndata'
  label: string
  objectPath: string
  // Where this AnnData keeps its level part: uns["apb"], or uns["protein"]["apb"] in an H5AD.
  unsKey: string
  // A standalone H5AD's root part, kept apart in uns["apb"].
  rootUns?: ApbMetadata
  diagram: AnnDataDiagram
  hasStorage: boolean
  annotation: boolean
}

export interface MuDataStructure {
  kind: 'mudata'
  label: string
  objectPath: string
  uns: ApbMetadata
  hasStorage: boolean
  modalities: Array<{ name: string, objectPath: string, dimensions: Dimensions }>
  relations: FeatureRelation[]
}

export type StructureView = AnnDataStructure | MuDataStructure

// One result file's sidecar, as the page loaded it.
export interface ResultStructure {
  file: string
  representation: Representation
}

// The sidecars of a job's AnnData downloads: `x.h5ad.apb.json` and `x.h5mu.apb.json`. A
// Parquet or DuckDB result's sidecar describes no AnnData, so it is not loaded.
export const anndataSidecars = (names: string[]): string[] =>
  names.filter(name => /\.h5(ad|mu)\.apb\.json$/.test(name))

export const resultName = (sidecar: string): string => sidecar.slice(0, -SIDECAR_SUFFIX.length)

function expandValue (value: unknown, field: string): unknown {
  if (EMBEDDED_JSON_FIELDS.has(field) && typeof value === 'string') {
    try {
      const parsed: unknown = JSON.parse(value)
      if (parsed === null || typeof parsed !== 'object') return value
      value = parsed
    } catch {
      // Recorded rule or plan text that is not JSON stays the text it is.
      return value
    }
  }
  if (Array.isArray(value)) return value.map(item => expandValue(item, ''))
  if (value === null || typeof value !== 'object') return value
  return Object.fromEntries(Object.entries(value).map(([name, item]) => [name, expandValue(item, name)]))
}

// The sidecar as a Representation; refuses another format or version rather than misread it.
export function validatedRepresentation (document: unknown): Representation {
  const header = document !== null && typeof document === 'object' ? document as Record<string, unknown> : {}
  if (header.format !== REPRESENTATION_FORMAT) {
    throw new Error(`Unsupported APB representation format: ${String(header.format ?? 'missing')}`)
  }
  if (header.format_version !== REPRESENTATION_VERSION) {
    throw new Error(`Unsupported APB representation version: ${String(header.format_version ?? 'missing')}`)
  }
  return expandValue(header, '') as Representation
}

function hierarchyOrder (representation: Representation): string[] {
  const hierarchy = representation.root?.apb?.hierarchy ?? representation.levels[0]?.apb?.hierarchy
  return (hierarchy?.identities ?? []).map(([name]) => name)
}

export function annDataDiagram (level: Partial<Level>): AnnDataDiagram {
  const logical = level.layers ?? []
  const primary = logical.find(layer => layer.storage_slot === 'X') ?? logical.find(layer => layer.primary === true) ?? null
  const aligned = level.aligned ?? {}
  return {
    name: level.name ?? 'unnamed',
    dimensions: level.dimensions ?? { observations: 0, variables: 0 },
    x: primary,
    layers: logical.filter(layer => layer.storage_slot !== 'X'),
    obs: level.obs ?? { row_count: 0, key_columns: [], columns: [] },
    var: level.var ?? { row_count: 0, key_columns: [], columns: [] },
    aligned: { obsm: aligned.obsm ?? [], varm: aligned.varm ?? [], obsp: aligned.obsp ?? [], varp: aligned.varp ?? [] },
    uns: level.apb ?? {}
  }
}

// Each physical AnnData apart from its MuData container: the container first, then every
// level in hierarchy order, then the annotation tables an H5MU embeds as AnnData.
export function structureViews (representation: Representation): StructureView[] {
  const order = hierarchyOrder(representation)
  const levels = [...representation.levels].sort((left, right) => order.indexOf(left.name) - order.indexOf(right.name))
  const embedded = representation.artifact?.physical_format === 'h5mu'
  const modalities: AnnDataStructure[] = levels.map(level => ({
    kind: 'anndata',
    label: `AnnData · ${level.name}`,
    objectPath: embedded ? `mdata.mod[${JSON.stringify(level.name)}]` : 'adata',
    unsKey: embedded ? 'uns["apb"]' : `uns[${JSON.stringify(level.name)}]["apb"]`,
    ...(embedded ? {} : { rootUns: representation.root?.apb ?? {} }),
    diagram: annDataDiagram(level),
    hasStorage: true,
    annotation: false
  }))
  if (!embedded) return modalities
  const reference = levels[0]
  for (const table of representation.annotation_tables ?? []) {
    // An annotation AnnData shares the first level's obs and has no X or uns.
    const name = `annotation/${table.name}`
    const diagram = annDataDiagram({
      name,
      dimensions: { observations: reference?.dimensions.observations ?? 0, variables: table.row_count },
      obs: reference?.obs,
      var: table
    })
    diagram.uns = {}
    modalities.push({
      kind: 'anndata',
      label: `AnnData · ${name}`,
      // The sidecar records logical names, not the encoded physical annotation keys.
      objectPath: `mdata.mod · annotation table ${JSON.stringify(table.name)}`,
      unsKey: 'uns["apb"]',
      diagram,
      hasStorage: false,
      annotation: true
    })
  }
  return [{
    kind: 'mudata',
    label: 'MuData container',
    objectPath: 'mdata',
    uns: representation.root?.apb ?? {},
    hasStorage: true,
    modalities: modalities.map(view => ({ name: view.diagram.name, objectPath: view.objectPath, dimensions: view.diagram.dimensions })),
    relations: representation.feature_relations ?? []
  }, ...modalities]
}

const finite = (value: unknown): number | null => (Number.isFinite(Number(value)) && value !== null ? Number(value) : null)

const total = (...values: Array<number | null | undefined>): number | null =>
  values.some(value => finite(value) !== null) ? values.reduce<number>((sum, value) => sum + (finite(value) ?? 0), 0) : null

export function matrixSummary (layer: Layer): {
  name: string
  role: string
  shape: Dimensions
  dtype: string
  kind: string
  totalCount: number | null
  finiteCount: number | null
  missingCount: number | null
  infiniteCount: number | null
  zeroCount: number | null
  mean: number | null
  median: number | null
  minimum: number | null
  maximum: number | null
} {
  const statistics = layer.statistics ?? {}
  return {
    name: layer.name,
    role: layer.role,
    shape: layer.shape,
    dtype: layer.dtype ?? 'unknown',
    kind: [layer.value_kind, layer.unit, layer.scale].filter(part => part !== null && part !== undefined && part !== '').join(' · '),
    totalCount: finite(statistics.total_count),
    finiteCount: finite(statistics.finite_count),
    missingCount: total(statistics.null_count, statistics.nan_count),
    infiniteCount: total(statistics.positive_infinity_count, statistics.negative_infinity_count),
    zeroCount: finite(statistics.zero_count),
    mean: finite(statistics.mean),
    median: finite(statistics.median),
    minimum: finite(statistics.minimum),
    maximum: finite(statistics.maximum)
  }
}
