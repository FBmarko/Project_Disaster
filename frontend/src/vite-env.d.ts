/// <reference types="vite/client" />
/// <reference types="google.maps" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_GOOGLE_MAPS_API_KEY?: string
  readonly VITE_GOOGLE_MAPS_MAP_ID?: string
}

interface Window {
  gm_authFailure?: () => void
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
