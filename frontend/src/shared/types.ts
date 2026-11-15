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
  /** The caller's role: they created it, or it was shared with them. */
  role: 'owner' | 'member'
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
  /** The ticket (or other) context that was allowed to steer the ranking. */
  context: string
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

/* ------------------------------------------------------------------ tickets */

export type TicketStatus = 'todo' | 'in_progress' | 'done'
export type TicketPriority = 'low' | 'medium' | 'high'

/** A person, by name — the only identity this build has. */
export interface Member {
  id: string
  display_name: string
}

export interface ProjectMember extends Member {
  role: 'owner' | 'member'
  added_at: string | null
}

/** One document Graph AI Search found for a ticket. */
export interface TicketFileHit {
  file_id: string
  name: string
  path: string
  directory_id: string
  directory_path: string
  score: number
  matched_terms: string[]
  excerpt: string
}

/** A document deliberately put on the ticket. */
export interface AttachedFile {
  file_id: string
  name: string
  path: string
  directory_path: string
  size_bytes: number
  added_at: string | null
  added_by: Member | null
  source: 'upload' | 'existing' | string
}

export interface TicketFiles {
  query: string
  context: string
  suggested: TicketFileHit[]
  attached: AttachedFile[]
  /** When the cached search last ran. */
  cached_at: string | null
  /** The stored result no longer matches the ticket or the project. */
  stale: boolean
  /** Why there is nothing to suggest (for example a ticket with no description). */
  reason: string | null
}

export interface Ticket {
  id: string
  project_id: string
  project_name: string
  number: number
  title: string
  description: string
  status: TicketStatus
  priority: TicketPriority
  due_date: string | null
  labels: string[]
  assignee: Member | null
  reporter: Member | null
  completed_at: string | null
  completed_by: Member | null
  attachment_count: number
  comment_count: number
  created_at: string | null
  updated_at: string | null
}

export interface TicketComment {
  id: string
  body: string
  author: Member | null
  created_at: string | null
}

export interface TicketDetail extends Ticket {
  comments: TicketComment[]
  files: TicketFiles
}

export interface TicketInput {
  projectId: string
  title: string
  description?: string
  assigneeId?: string | null
  priority?: TicketPriority
  dueDate?: string | null
  labels?: string[]
}

export interface TicketPatch {
  title?: string
  description?: string
  assigneeId?: string | null
  priority?: TicketPriority
  dueDate?: string | null
  labels?: string[]
}

/** One line of the changes-and-updates feed. */
export interface TicketEvent {
  id: string
  kind: string
  detail: Record<string, unknown>
  project_id: string
  ticket_id: string | null
  ticket_number: number | null
  actor: Member | null
  created_at: string | null
}

/* ------------------------------------------------------------------- chat */

/** What a chat message may point at. */
export type MentionKind = 'file' | 'directory' | 'ticket' | 'event'

/** A reference stored with a message (mirrors the backend's MentionOut). */
export interface ChatMention {
  kind: MentionKind
  id: string
  label: string
  /** The document's or folder's path; empty for a ticket or an event. */
  path: string
  /** The folder a document lives in, so the graph can reveal it directly. */
  directory_path: string
  ticket_number: number | null
  /** The day a calendar event sits on (`YYYY-MM-DD`), when the mention is an event. */
  event_day: string | null
}

export interface ChatMessage {
  seq: number
  id: string
  project_id: string
  author: Member | null
  body: string
  mentions: ChatMention[]
  created_at: string | null
  /** The author (or the project owner) removed it. */
  deleted: boolean
}

/** A project's group chat. */
export interface ChatChannel {
  project_id: string
  project_name: string
  last_message: ChatMessage | null
  last_activity_at: string | null
}

/** One thing the composer may offer after an `@`. */
export interface MentionTarget {
  kind: MentionKind
  id: string
  label: string
  path: string
  directory_path: string
  ticket_number: number | null
  /** The day an event sits on (`YYYY-MM-DD`), when the target is a calendar event. */
  event_day: string | null
  detail: string
}

/* --------------------------------------------------------------- calendar */

export interface CalendarPerson {
  id: string
  display_name: string
}

/** A document, folder or ticket an event's notes point at (mirrors EventMentionOut). */
export interface CalendarMention {
  kind: Exclude<MentionKind, 'event'>
  id: string
  label: string
  /** The document's or folder's path; empty for a ticket. */
  path: string
  /** The folder a document lives in, so the graph can reveal it directly. */
  directory_path: string
  /** The ticket's number, when the mention is a ticket. */
  ticket_number: number | null
}

/** One thing on a day: an added event, or a ticket's deadline. */
export interface CalendarItem {
  kind: 'event' | 'deadline'
  id: string
  title: string
  /** ISO date (`YYYY-MM-DD`). */
  day: string
  project_id: string | null
  project_name: string
  starts_at: string | null
  ends_at: string | null
  all_day: boolean
  notes: string
  /** Only an event the caller added can be edited or deleted. */
  editable: boolean
  created_by: CalendarPerson | null
  ticket_id: string | null
  ticket_number: number | null
  status: TicketStatus | null
  priority: TicketPriority | null
  assignee: CalendarPerson | null
  /** Documents, folders and tickets the event's notes mention. */
  mentions: CalendarMention[]
}

export interface CalendarRange {
  scope: 'personal' | 'project'
  project_id: string | null
  project_name: string
  start: string
  end: string
  items: CalendarItem[]
}

export interface CalendarEventInput {
  /** Set for a project event; omit (or null) for a personal one. */
  projectId?: string | null
  title: string
  notes?: string
  startsAt: string
  endsAt?: string | null
  allDay?: boolean
}

export interface CalendarEventPatch {
  title?: string
  notes?: string
  startsAt?: string
  endsAt?: string | null
  allDay?: boolean
}

export interface CalendarEvent {
  id: string
  project_id: string | null
  project_name: string
  title: string
  notes: string
  starts_at: string
  ends_at: string | null
  all_day: boolean
  created_by: CalendarPerson | null
  created_at: string | null
  updated_at: string | null
  /** The documents, folders and tickets the notes mention (resolved when it was saved). */
  mentions: CalendarMention[]
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

/**
 * A document written in the app that does not exist in the graph yet.
 *
 * It travels to the same Graph Add endpoint an upload does: the main process turns `text`
 * into the bytes of a markdown multipart part, so the backend never learns whether the
 * document came from disk or from the editor.
 */
export interface DraftSuggestionInput {
  projectId: string
  /** The name to store it under, with a markdown suffix (`release-checklist.md`). */
  fileName: string
  text: string
  /** A ticket's title and description, which may steer the ranking. */
  context?: string
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
    suggest(input: {
      projectId: string
      filePath: string
      /** A ticket's title and description, which may steer the ranking. */
      context?: string
    }): Promise<ApiResult<SuggestionAccepted>>
    /** Rank the folders for a document written in the app (no file on disk). */
    suggestDraft(input: DraftSuggestionInput): Promise<ApiResult<SuggestionAccepted>>
    place(input: PlacementInput): Promise<ApiResult<PlacementResult>>
  }
  search: {
    run(input: { projectId: string; query: string; limit?: number }): Promise<ApiResult<SearchResults>>
  }
  tickets: {
    members(): Promise<ApiResult<Member[]>>
    signIn(displayName: string): Promise<ApiResult<Member>>
    me(): Promise<ApiResult<Member>>
    list(input: {
      scope?: 'mine' | 'project'
      projectId?: string
      status?: TicketStatus | null
      limit?: number
    }): Promise<ApiResult<Ticket[]>>
    create(input: TicketInput): Promise<ApiResult<Ticket>>
    get(ticketId: string, refresh?: boolean): Promise<ApiResult<TicketDetail>>
    update(ticketId: string, patch: TicketPatch): Promise<ApiResult<Ticket>>
    setStatus(ticketId: string, status: TicketStatus): Promise<ApiResult<Ticket>>
    files(ticketId: string, refresh?: boolean): Promise<ApiResult<TicketFiles>>
    attach(
      ticketId: string,
      fileId: string,
      source?: 'upload' | 'existing'
    ): Promise<ApiResult<TicketFiles>>
    detach(ticketId: string, fileId: string): Promise<ApiResult<null>>
    comment(ticketId: string, body: string): Promise<ApiResult<TicketComment>>
    activity(input: {
      projectId?: string
      ticketId?: string
      limit?: number
    }): Promise<ApiResult<TicketEvent[]>>
    projectMembers(projectId: string): Promise<ApiResult<ProjectMember[]>>
    share(projectId: string, memberId: string): Promise<ApiResult<Member>>
    unshare(projectId: string, memberId: string): Promise<ApiResult<null>>
  }
  shell: {
    openExternal(url: string): Promise<void>
  }
  chat: {
    channels(): Promise<ApiResult<ChatChannel[]>>
    messages(input: {
      projectId: string
      /** Only messages newer than this seq (the poll cursor). */
      afterSeq?: number
      limit?: number
    }): Promise<ApiResult<ChatMessage[]>>
    post(projectId: string, body: string): Promise<ApiResult<ChatMessage>>
    remove(messageId: string): Promise<ApiResult<null>>
    mentionTargets(input: {
      projectId: string
      query?: string
      limit?: number
    }): Promise<ApiResult<MentionTarget[]>>
  }
  calendar: {
    personal(input: { from: string; to: string }): Promise<ApiResult<CalendarRange>>
    project(input: {
      projectId: string
      from: string
      to: string
    }): Promise<ApiResult<CalendarRange>>
    create(input: CalendarEventInput): Promise<ApiResult<CalendarEvent>>
    update(eventId: string, patch: CalendarEventPatch): Promise<ApiResult<CalendarEvent>>
    remove(eventId: string): Promise<ApiResult<null>>
    /** Documents, folders and tickets an event's notes may mention after an `@`. */
    mentionTargets(input: {
      projectId: string
      query?: string
      limit?: number
    }): Promise<ApiResult<MentionTarget[]>>
    /** The events whose notes mention one document, folder or ticket (a ticket's meetings). */
    mentioning(input: {
      projectId: string
      kind: 'file' | 'directory' | 'ticket'
      id: string
    }): Promise<ApiResult<CalendarItem[]>>
  }

}