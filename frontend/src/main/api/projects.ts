/** Graph Creation reads: the project list, one project, the depth-limited tree, and
 *  one directory's immediate children (used when a node is expanded). */

import type { CreationJob, DirectoryChildren, Project, ProjectTree } from '../../shared/types'
import { request } from './client'

const CREATION = '/api/graph-creation'

const id = encodeURIComponent

export const listProjects = (): Promise<Project[]> => request(`${CREATION}/projects`)

export const getProject = (projectId: string): Promise<Project> =>
  request(`${CREATION}/projects/${id(projectId)}`)

export const getTree = (projectId: string, depth: number): Promise<ProjectTree> =>
  request(`${CREATION}/projects/${id(projectId)}/tree?depth=${depth}`)

export const getDirectory = (directoryId: string): Promise<DirectoryChildren> =>
  request(`${CREATION}/directories/${id(directoryId)}`)

export const getJob = (jobId: string): Promise<CreationJob> => request(`${CREATION}/jobs/${id(jobId)}`)