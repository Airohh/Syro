import { ClassificationResult } from '../services/profileService';
import { getDomainConfig } from '../utils/domainConfig';

interface ClassificationPreviewProps {
  classification: ClassificationResult;
  onDomainChange?: (domain: string) => void;
  editable?: boolean;
}

export default function ClassificationPreview({
  classification,
  onDomainChange,
  editable = false,
}: ClassificationPreviewProps) {
  const domainConfig = getDomainConfig(classification.domain);
  const confidencePercent = Math.round(classification.confidence * 100);
  const confidenceColor =
    classification.confidence >= 0.7
      ? 'text-green-600'
      : classification.confidence >= 0.5
      ? 'text-yellow-600'
      : 'text-red-600';

  const confidenceBg =
    classification.confidence >= 0.7
      ? 'bg-green-100'
      : classification.confidence >= 0.5
      ? 'bg-yellow-100'
      : 'bg-red-100';

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-700">Classification automatique</h4>
        <span className={`px-2 py-1 rounded text-xs font-semibold ${confidenceBg} ${confidenceColor}`}>
          {confidencePercent}% de confiance
        </span>
      </div>

      <div className="space-y-2">
        <div className="flex items-center">
          <span className="text-sm text-gray-600 mr-2">Domaine détecté:</span>
          {editable && onDomainChange ? (
            <select
              value={classification.domain}
              onChange={(e) => onDomainChange(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
            >
              <option value="general">Général</option>
              <option value="medical">Médical</option>
              <option value="legal">Juridique</option>
              <option value="finance">Finance</option>
              <option value="education">Éducation</option>
              <option value="tech">Tech</option>
            </select>
          ) : (
            <span className="font-semibold text-gray-900">{domainConfig.name}</span>
          )}
        </div>

        {classification.alternatives.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-500 mb-2">Alternatives possibles:</p>
            <div className="space-y-1">
              {classification.alternatives.map((alt, idx) => (
                <div key={idx} className="flex justify-between text-xs">
                  <span className="text-gray-600 capitalize">{alt.domain}</span>
                  <span className="text-gray-500">{Math.round(alt.confidence * 100)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {classification.confidence < 0.7 && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <p className="text-xs text-yellow-600">
              ⚠️ Confiance faible. Vérifiez que le domaine est correct.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

