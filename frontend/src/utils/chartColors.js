/**
 * Couleurs adaptatives pour les graphiques selon le thème
 */

export const getChartColors = (theme) => {
  const isDark = theme === 'dark';
  
  return {
    // Grille et axes
    grid: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)',
    axis: isDark ? '#888' : '#666',
    
    // Ligne principale
    primary: isDark ? '#60a5fa' : '#3b82f6',      // blue-400 / blue-500
    primaryGradient: {
      start: isDark ? 'rgba(96, 165, 250, 0.3)' : 'rgba(59, 130, 246, 0.3)',
      end: isDark ? 'rgba(96, 165, 250, 0.0)' : 'rgba(59, 130, 246, 0.0)',
    },
    
    // Zone de confiance
    confidence: isDark ? 'rgba(147, 197, 253, 0.15)' : 'rgba(191, 219, 254, 0.3)',
    confidenceBorder: isDark ? '#93c5fd' : '#bfdbfe',
    
    // Tendances et statuts
    positive: isDark ? '#4ade80' : '#22c55e',     // green-400 / green-500
    negative: isDark ? '#f87171' : '#ef4444',     // red-400 / red-500
    neutral: isDark ? '#a3a3a3' : '#737373',      // neutral-400 / neutral-500
    warning: isDark ? '#fbbf24' : '#f59e0b',      // amber-400 / amber-500
    
    // Tooltip
    tooltip: {
      background: isDark ? '#1f2937' : '#ffffff',  // gray-800 / white
      border: isDark ? '#374151' : '#e5e7eb',      // gray-700 / gray-200
      text: isDark ? '#f9fafb' : '#111827',        // gray-50 / gray-900
      label: isDark ? '#d1d5db' : '#6b7280',       // gray-300 / gray-500
    },
    
    // Référence ligne zéro
    referenceLine: isDark ? '#ef4444' : '#dc2626', // red-500 / red-600
  };
};

// Hook pour utiliser les couleurs dans les composants
export const useChartColors = (theme) => {
  return getChartColors(theme || 'light');
};
