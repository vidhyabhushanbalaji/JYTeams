/** The channel list: every project the caller can see, with the last thing said in each. */

import { useCallback, useEffect, useState } from 'react'

import type { ApiError, ChatChannel } from '@shared/types'

export function useChatChannels(revision = 0) {
  const [channels, setChannels] = useState<ChatChannel[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<ApiError | null>(null)

  const reload = useCallback(async (): Promise<void> => {
    setLoading(true)
    setError(null)
    const result = await window.jyteams.chat.channels()
    if (result.ok) {
      setChannels(result.data)
    } else {
      setChannels([])
      setError(result.error)
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    void reload()
  }, [reload, revision])

  return { channels, loading, error, reload }
}
