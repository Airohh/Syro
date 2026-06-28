/// <reference types="vite/client" />
// Source unique de l'URL backend (ADR-001 : multi-domaines = 1 API).
// Le domaine n'est plus porté par un port mais par la route /domains/{domain}/...
// Les fonctions gardent leur signature historique pour compat des appelants.
const API_BASE_URL: string =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

function _port(): number {
  const p = new URL(API_BASE_URL).port;
  return p ? Number(p) : 8000;
}

export function getDomainPort(_domainId?: string): number {
  return _port();
}

export function getDomainApiUrl(_domainId?: string): string {
  return API_BASE_URL;
}
