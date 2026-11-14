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
  proposed_new_directory_names: string[]
  name_available: boolean
  suggested_file_names: string[]
  identical_content_at: string[]
}

export interface TraversalInfo {
  expanded: number
  visited: number
  degraded: boolean
  budget_exhausted: boolean
  model: string
}

export interface DocumentBrief {
  name: string
  size_bytes: number
  content_sha256: string
  summary: string
}

export interface SuggestionAccepted {
  request_id: string
  project_id: string
  status: string
  expires_at: string | null
  file: DocumentBrief
  suggestions: AddSuggestion[]
  traversal: TraversalInfo
}

export type PlacementMode = 'direct' | 'new_directory'

export interface PlacementInput {
  request_id: string
  directory_id: string
  placement: PlacementMode
  new_directory_name?: string | null
  file_name?: string | null
}

export interface PlacementResult {
  project_id: string
  request_id: string
  directory_id: string
  directory_path: string
  created_directory: boolean
  refreshed_directories: number
  file: ProjectFile
}

export interface SearchHit {
  file_id: string
  name: string
  path: string
  directory_id: string
  directory_path: string
  summary: string
  score: number
  reason: string
}

export interface SearchTraversal {
  directories_visited: number
  directories_opened: number
  documents_considered: number
  fallback_used: boolean
  degraded: boolean
  budget_exhausted: boolean
  model: string
}

export interface SearchResults {
  query: string
  project_id: string
  results: SearchHit[]
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