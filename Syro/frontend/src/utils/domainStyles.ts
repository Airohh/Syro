/**
 * Helper pour mapper les domaines aux classes Tailwind
 * Nécessaire car Tailwind ne peut pas détecter les classes générées dynamiquement
 */

export const getDomainClasses = (domainId: string) => {
  const classMap: Record<string, {
    bg: string;
    bgLight: string;
    text: string;
    border: string;
  }> = {
    tech: {
      bg: 'bg-[#2563eb]',           // Blue 600
      bgLight: 'bg-[#dbeafe]',      // Blue 100
      text: 'text-[#2563eb]',        // Blue 600
      border: 'border-[#2563eb]',    // Blue 600
    },
    medical: {
      bg: 'bg-[#059669]',           // Emerald 600
      bgLight: 'bg-[#d1fae5]',      // Emerald 100
      text: 'text-[#059669]',        // Emerald 600
      border: 'border-[#059669]',    // Emerald 600
    },
    legal: {
      bg: 'bg-[#7c3aed]',           // Violet 600
      bgLight: 'bg-[#ede9fe]',      // Violet 100
      text: 'text-[#7c3aed]',       // Violet 600
      border: 'border-[#7c3aed]',   // Violet 600
    },
    finance: {
      bg: 'bg-[#d97706]',           // Amber 600
      bgLight: 'bg-[#fef3c7]',      // Amber 100
      text: 'text-[#d97706]',       // Amber 600
      border: 'border-[#d97706]',   // Amber 600
    },
    education: {
      bg: 'bg-[#db2777]',           // Pink 600
      bgLight: 'bg-[#fce7f3]',      // Pink 100
      text: 'text-[#db2777]',       // Pink 600
      border: 'border-[#db2777]',   // Pink 600
    },
    general: {
      bg: 'bg-gray-900',
      bgLight: 'bg-gray-100',
      text: 'text-gray-900',
      border: 'border-gray-900',
    },
  };

  return classMap[domainId] || classMap.general;
};

