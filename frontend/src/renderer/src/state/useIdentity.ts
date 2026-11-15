/** Who the app is. A name, stored as the dev user id — there is no password. */

import { useCallback, useEffect, useState } from 'react'

import type { ApiError, ApiResult, Member } from '@shared/types'

export type IdentityStatus = 'loading' | 'signedOut' | 'ready' | 'error'

export interface Identity {
  status: IdentityStatus
  member: Member | null
  /** Every name that can be picked (the startup list). */
  members: Member[]
  error: ApiError | null
  reload: () => Promise<void>
  signIn: (displayName: string) => Promise<ApiResult<Member>>
  signOut: () => Promise<void>
}

export function useIdentity(): Identity {
  const [status, setStatus] = useState<IdentityStatus>('loading')
  const [member, setMember] = useState<Member | null>(null)
  const [members, setMembers] = useState<Member[]>([])
  const [error, setError] = useState<ApiError | null>(null)

  const loadMembers = useCallback(async (): Promise<void> => {
    const result = await window.jyteams.tickets.members()
    if (result.ok) setMembers(result.data)
  }, [])

  const reload = useCallback(async (): Promise<void> => {
    setStatus('loading')
    setError(null)
    const result = await window.jyteams.tickets.me()
    if (result.ok) {
      setMember(result.data)
      setStatus('ready')
    } else if (result.error.status === 404) {
      // The stored identity is not a member (fresh install, or a name that was never created).
      setMember(null)
      setStatus('signedOut')
    } else {
      setMember(null)
      setError(result.error)
      setStatus('error')
    }
    await loadMembers()
  }, [loadMembers])

  useEffect(() => {
    void reload()
  }, [reload])

  const signIn = useCallback(
    async (displayName: string): Promise<ApiResult<Member>> => {
      const result = await window.jyteams.tickets.signIn(displayName)
      if (result.ok) {
        await window.jyteams.config.set({ devUserId: result.data.id })
        setMember(result.data)
        setStatus('ready')
        setError(null)
        await loadMembers()
      } else {
        setError(result.error)
      }
      return result
    },
    [loadMembers]
  )

  const signOut = useCallback(async (): Promise<void> => {
    await window.jyteams.config.set({ devUserId: '' })
    setMember(null)
    setStatus('signedOut')
  }, [])

  return { status, member, members, error, reload, signIn, signOut }
}
