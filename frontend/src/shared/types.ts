/**
 * The contract shared by the main process, the preload bridge and the renderer.
 *
 * Every shape here mirrors a FastAPI model field for field:
 *   backend/app/graph_creation/schemas.py  -> Project, Directory, ProjectFile, CreationJob
 *   backend/app/graph_add/schemas.py       -> SuggestionAccepted, PlacementInput/Out
 *   backend/app/graph_ai_search/schemas.py -> SearchResults
 * Nothing here is invented: if the backend changes, this file has to follow.
 */

export interface XYPosition {
  x: number
  y: number
}

export interface Project {
  id: string
  name: string
  description: string | null
  root_directory_id: string | null
  created_at: string | null
}

export interface ProjectFile {
  id: string
  name: string
  path: string
  size_bytes: number
  summary: string | null
  summary_status: string
  storage_bucket: string | null
  storage_path: string | null
}

export interface Directory {
  id: string
  name: string
  path: string
  depth: number
  description: string | null
  direct_file_count: number
  child_directory_count: number
  files: ProjectFile[]
  directories: Directory[]
}

export interface ProjectTree {
  project: Project
  tree: Directory
}

export interface DirectoryChildren {
  directory: Directory
  files: ProjectFile[]
  directories: Directory[]
}

/** A document body as the viewer receives it (mirrors the backend's FileContentOut). */
export interface FileContent {
  id: string
  name: string
  path: string
  size_bytes: number
  content_sha256: string
  text: string
  /** Markdown and within the read cap; otherwise the sheet is read-only. */
  editable: boolean
  /** The stored text exceeded the read cap, so `text` was cut for display. */
  truncated: boolean
}

/** What the sheet sends to save a document (mirrors FileContentIn). */
export interface FileContentInput {
  fileId: string
  text: string
  /** The digest that was read; a mismatch refuses the write, so nothing stale overwrites it. */
  expectedSha256?: string | null
}

/** The row after a save (mirrors the backend's FileSavedOut). */
export interface FileSaved extends ProjectFile {
  content_sha256: string
}

export interface CreationJob {
  id: string
  project_id: string
  mode: string
  status: 'queued' | 'summarising' | 'persisting' | 'ok' | 'partial' | 'failed'
  total_files: number
  processed_files: number
  failed_files: number
  error: string | null
  created_at: string | null
  finished_at: string | null
}

export interface UploadAccepted {
  project_id: string
  job_id: string
  mode: string
  total_files: number
}

export interface AddSuggestion {
  rank: number
  score: number
  directory_id: string
  path: string
  name: string
  depth: number
  description: string | null
  direct_file_count: number
  child_directory_count: number
  is_leaf: boolean
  reason: string
  /** The document's own words that the folder matched, so the score is explainable. */
  matched_terms: string[]
  proposed_new_directory_names: string[]
  name_available: boolean
  suggested_file_names: string[]
  identical_content_at: string[]
}

/** What the local folder scan cost (no model was called). */
export interface ScanInfo {
  folders_scored: number
  threshold: number
  scorer_version: string
}

/** The uploaded document as the client last saw it. */
export interface DocumentBrief {
  name: string
  size_bytes: number
  content_sha256: string
  /** First ~200 characters of the document — no model wrote it, so it is always faithful. */
  preview: string
}

export interface SuggestionAccepted {
  request_id: string
  project_id: string
  status: string
  expires_at: string | null
  file: DocumentBrief
  suggestions: AddSuggestion[]
  scan: ScanInfo
}

export type PlacementMode = 'direct' | 'new_directory'

export interface PlacementInput {
  request_id: string
  directory_id: string
  placement: PlacementMode
  new_directory_name?: string | null
  file_name?: string | null
}

/** The file row a placement wrote (documents are stored, never summarised). */
export interface PlacedFile {
  id: string
  name: string
  path: string
  directory_id: string
  size_bytes: number
  summary_status: string
  storage_bucket: string | null
  storage_path: string | null
}

export interface PlacementResult {
  project_id: string
  request_id: string
  directory_id: string
  directory_path: string
  created_directory: boolean
  /** Folders whose description was refreshed (one model call covered all of them). */
  refreshed_directories: number
  file: PlacedFile
}

export interface SearchHit {
  file_id: string
  name: string
  path: string
  directory_id: string
  directory_path: string
  score: number
  /** Query terms found in the document (or its name), so the score is explainable. */
  matched_terms: string[]
  /** A snippet around the first match — no model summarised it, so it is always faithful. */
  excerpt: string
}

/** A folder worth browsing, judged from its stored description. */
export interface DirectoryHit {
  directory_id: string
  path: string
  name: string
  depth: number
  score: number
  matched_terms: string[]
}

export interface SearchTraversal {
  directories_visited: number
  directories_opened: number
  documents_considered: number
  /** Documents whose stored text was actually read (the expensive part of a search). */
  files_read: number
  fallback_used: boolean
  degraded: boolean
  budget_exhausted: boolean
  /** Identifies the local scorer that produced the ordering. */
  scorer_version: string
  duration_ms: number
}

export interface SearchResults {
  query: string
  context: string
  project_id: string
  results: SearchHit[]
  /** Folders whose descriptions matched, so the UI can offer "browse this instead". */
  directories: DirectoryHit[]
  opened_directories: string[]
  traversal: SearchTraversal
}

/** A failure normalised by the main process; never thrown across IPC. */
export interface ApiError {
  /** HTTP status, or 0 when the backend could not be reached at all. */
  status: number
  message: string
  /** The FastAPI `detail` payload, when one was returned. */
  detail: unknown
}

export type ApiResult<T> = { ok: true; data: T } | { ok: false; error: ApiError }

export interface AppConfig {
  baseUrl: string
  devUserId: string
  bearerToken: string
}

export interface HealthReport {
  api: boolean
  supabase: boolean
  apiDetail: string
  supabaseDetail: string
}

export interface PickedFile {
  path: string
  name: string
  sizeBytes: number
}

export interface FolderPreview {
  path: string
  name: string
  fileCount: number
  totalBytes: number
  skippedCount: number
  problems: string[]
}

/** The surface exposed on `window.jyteams` by the preload script. */
export interface JyTeamsApi {
  config: {
    get(): Promise<AppConfig>
    set(patch: Partial<AppConfig>): Promise<AppConfig>
  }
  health: {
    ping(): Promise<HealthReport>
  }
  projects: {
    list(): Promise<ApiResult<Project[]>>
    get(id: string): Promise<ApiResult<Project>>
    tree(id: string, depth: number): Promise<ApiResult<ProjectTree>>
    directory(id: string): Promise<ApiResult<DirectoryChildren>>
    job(id: string): Promise<ApiResult<CreationJob>>
  }
  files: {
    read(fileId: string): Promise<ApiResult<FileContent>>
    save(input: FileContentInput): Promise<ApiResult<FileSaved>>
  }
  layout: {
    load(projectId: string): Promise<Record<string, XYPosition>>
    save(projectId: string, positions: Record<string, XYPosition>): Promise<void>
    clear(projectId: string): Promise<void>
  }
  create: {
    pickFolder(): Promise<string | null>
    preview(folderPath: string): Promise<ApiResult<FolderPreview>>
    upload(input: { name: string; folderPath: string }): Promise<ApiResult<UploadAccepted>>
  }
  add: {
    pickFile(): Promise<PickedFile | null>
    suggest(input: { projectId: string; filePath: string }): Promise<ApiResult<SuggestionAccepted>>
    place(input: PlacementInput): Promise<ApiResult<PlacementResult>>
  }
  search: {
    run(input: { projectId: string; query: string; limit?: number }): Promise<ApiResult<SearchResults>>
  }
  shell: {
    openExternal(url: string): Promise<void>
  }
}