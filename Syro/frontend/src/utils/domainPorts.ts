// Mapping des domaines vers les ports de l'API
// NOTE: Tous les domaines utilisent maintenant le même backend (port 8000)
// avec des routes multi-domaines : /domains/{domain}/...
export const DOMAIN_PORTS: Record<string, number> = {
  tech: 8000,
  medical: 8000,  // Même backend, route /domains/medical/...
  legal: 8000,    // Même backend, route /domains/legal/...
  finance: 8000,  // Même backend, route /domains/finance/...
  education: 8000, // Même backend, route /domains/education/...
  general: 8000,
};

export function getDomainPort(_domainId: string): number {
  // Tous les domaines utilisent le port 8000 maintenant
  // Le paramètre _domainId est conservé pour la compatibilité avec le code existant
  return 8000;
}

export function getDomainApiUrl(_domainId: string): string {
  // Tous les domaines utilisent le même backend sur le port 8000
  // Les routes multi-domaines sont gérées par le backend
  // Le paramètre _domainId est conservé pour la compatibilité avec le code existant
  return `http://localhost:8000`;
}

