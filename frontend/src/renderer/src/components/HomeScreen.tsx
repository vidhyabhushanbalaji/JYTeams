import { useMemo, useState } from 'react'

import { describeError } from '../lib/errors'
import { shortDate } from '../lib/format'
import { useProjects } from '../state/useProjects'
import { NewProjectFlow } from './NewProjectFlow'
import { Empty, ErrorBox, Spinner } from './primitives'

export function HomeScreen({
  onOpenProject,
  onOpenSettings,
  notify
}: {
  onOpenProject: (projectId: string) => void
  onOpenSettings: () => void
  notify: (message: string, tone?: 'info' | 'error') => void
}) {
  const { projects, loading, error, reload } = useProjects()
  const [filter, setFilter] = useState('')
  const [creating, setCreating] = useState(false)

  const visible = useMemo(() => {
    const needle = filter.trim().toLowerCase()
    if (!needle) return projects
    return projects.filter((project) =>
      `${project.name} ${project.description ?? ''}`.toLowerCase().includes(needle)
    )
  }, [projects, filter])

  return (
    <div className="screen">
      <div className="screen__inner">
        <header className="screen__head">
          <div>
            <h1 className="screen__title">Projects</h1>
            <p className="screen__lede">
              Every project is a tree of markdown folders and files, described from the bottom up,
              so you can find your way around it without opening anything.
            </p>
          </div>
          <div className="screen__actions">
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => void reload()}
              disabled={loading}
            >
              Refresh
            </button>
            <button type="button" className="btn btn--primary" onClick={() => setCreating(true)}>
              New project
            </button>
          </div>
        </header>

        {loading ? (
          <div className="empty">
            <Spinner label="Loading projects" />
          </div>
        ) : null}

        {!loading && error ? (
          <ErrorBox title="Projects could not be loaded" detail={describeError(error)}>
            <div className="screen__actions" style={{ marginLeft: 0 }}>
              <button type="button" className="btn btn--sm" onClick={() => void reload()}>
                Try again
              </button>
              <button type="button" className="btn btn--ghost btn--sm" onClick={onOpenSettings}>
                Settings
              </button>
            </div>
          </ErrorBox>
        ) : null}

        {!loading && !error ? (
          <>
            <div className="filter">
              <input
                className="filter__input"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                placeholder="Filter projects"
                aria-label="Filter projects"
              />
            </div>

            {projects.length === 0 ? (
              <Empty
                title="No projects yet"
                text="Choose a folder of markdown files and the tree is built and described for you. It is ready to browse as soon as the upload finishes."
              >
                <button type="button" className="btn btn--primary" onClick={() => setCreating(true)}>
                  Create the first project
                </button>
              </Empty>
            ) : (
              <ul className="project-list">
                {visible.map((project) => (
                  <li key={project.id}>
                    <button
                      type="button"
                      className="project-row"
                      onClick={() => onOpenProject(project.id)}
                    >
                      <span className="project-row__body">
                        <span className="project-row__name">{project.name}</span>
                        <span className="project-row__desc">
                          {project.description ?? 'No description yet.'}
                        </span>
                      </span>
                      <span className="project-row__meta">{shortDate(project.created_at)}</span>
                      <span className="project-row__go" aria-hidden="true">
                        {'\u2192'}
                      </span>
                    </button>
                  </li>
                ))}
                {visible.length === 0 ? (
                  <Empty title="No match" text="No project name or description contains that." />
                ) : null}
              </ul>
            )}
          </>
        ) : null}
      </div>

      <NewProjectFlow
        open={creating}
        onClose={() => setCreating(false)}
        onCreated={(projectId) => {
          setCreating(false)
          notify('Project created.')
          onOpenProject(projectId)
        }}
        onWarning={(message) => notify(message, 'error')}
      />
    </div>
  )
}