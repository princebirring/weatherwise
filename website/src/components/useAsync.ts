import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api'

export interface Async<T> {
  data: T | null
  error: ApiError | null
  loading: boolean
  retry: () => void
}

/** Runs `load` when `key` changes; a stale answer for an old key is ignored. */
export function useAsync<T>(load: (() => Promise<T>) | null, key: string): Async<T> {
  const [state, setState] = useState<{ key: string; data: T | null; error: ApiError | null }>({ key: '', data: null, error: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!load) return
    let live = true
    load().then(
      (data) => live && setState({ key, data, error: null }),
      (e) => live && setState({ key, data: null, error: e instanceof ApiError ? e : new ApiError('failed', String(e), 0) }),
    )
    return () => { live = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- `load` is recreated each render; `key` names the request
  }, [key, attempt])

  const retry = useCallback(() => {
    setState((s) => ({ ...s, key: '', error: null }))
    setAttempt((a) => a + 1)
  }, [])
  const current = state.key === key
  return { data: current ? state.data : null, error: current ? state.error : null, loading: !!load && !current, retry }
}
