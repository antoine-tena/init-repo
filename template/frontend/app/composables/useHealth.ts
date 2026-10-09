export interface HealthPayload {
  status: string
}

// [APPELS-API] : seul point d'appel de la route de santé du backend.
export function useHealth() {
  const config = useRuntimeConfig()
  return useFetch<HealthPayload>(`${config.public.apiBase}/health`, { key: 'health' })
}
