import React, { useState, useRef, useEffect } from 'react';
import { profileService, ClassificationResult } from '../services/profileService';
import { domainService } from '../services/api';
import ClassificationPreview from './ClassificationPreview';
import { getDomainConfig, domains } from '../utils/domainConfig';
import { getDomainPort } from '../utils/domainPorts';
import { getDomainClasses } from '../utils/domainStyles';
import { ChevronDown, Check, Upload } from 'lucide-react';

interface DocumentUploaderProps {
  onUploadSuccess?: () => void;
  currentDomain?: string;
}

export default function DocumentUploader({ onUploadSuccess, currentDomain = 'general' }: DocumentUploaderProps) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [classification, setClassification] = useState<ClassificationResult | null>(null);
  const [targetDomain, setTargetDomain] = useState<string>(currentDomain); // Domaine choisi pour l'upload
  const [showDomainSelector, setShowDomainSelector] = useState(false);
  
  // Mettre à jour targetDomain quand currentDomain change
  useEffect(() => {
    if (currentDomain) {
      console.log('[DocumentUploader] currentDomain changé:', currentDomain);
      setTargetDomain(currentDomain);
    }
  }, [currentDomain]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file: File) => {
    // Validation
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
      setError('Le fichier est trop volumineux (max 50MB)');
      return;
    }

    setSelectedFile(file);
    setError(null);
    setSuccess(false);
    setClassification(null);
    // Réinitialiser le domaine cible au domaine actuel
    setTargetDomain(currentDomain);
    setShowDomainSelector(true); // Afficher le sélecteur de domaine

    // Pré-classification (optionnel, peut être fait côté serveur)
    // Pour l'instant, on upload directement et le serveur fait la classification
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      setUploading(true);
      setError(null);
      setProgress(0);

      // Log pour déboguer
      console.log('[DocumentUploader] Upload vers domaine:', targetDomain);
      console.log('[DocumentUploader] Domaine actuel:', currentDomain);
      
      // Vérifier que le backend du domaine cible est disponible avant d'uploader
      try {
        console.log('[DocumentUploader] Vérification du backend pour:', targetDomain);
        await domainService.getHealth(targetDomain);
        console.log('[DocumentUploader] Backend OK pour:', targetDomain);
      } catch (healthError: any) {
        const domainConfig = getDomainConfig(targetDomain);
        const port = getDomainPort(targetDomain);
        console.error('[DocumentUploader] Backend non accessible:', targetDomain, 'port:', port);
        setError(`Le backend ${domainConfig.name} n'est pas accessible sur le port ${port}. Vérifiez qu'il est bien démarré.`);
        setUploading(false);
        return;
      }
      
      // Utiliser le domaine choisi par l'utilisateur
      console.log('[DocumentUploader] Démarrage de l\'upload vers:', targetDomain);
      const result = await profileService.uploadWithClassification(
        selectedFile,
        targetDomain,
        (prog) => setProgress(prog)
      );

      setClassification(result.classification);
      setSuccess(true);

      // Reset après 2 secondes
      setTimeout(() => {
        setSelectedFile(null);
        setClassification(null);
        setShowDomainSelector(false);
        setTargetDomain(currentDomain);
        setSuccess(false);
        setProgress(0);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }
        if (onUploadSuccess) {
          onUploadSuccess();
        }
      }, 2000);
    } catch (err: any) {
      console.error('Upload error:', err);
      // Afficher un message d'erreur plus clair
      let errorMessage = 'Erreur lors de l\'upload';
      
      if (err?.userMessage) {
        errorMessage = err.userMessage;
      } else if (err?.message) {
        // Nettoyer le message pour éviter les duplications
        errorMessage = err.message.replace(/le backend le backend/gi, 'le backend');
        errorMessage = errorMessage.replace(/backend backend/gi, 'backend');
      } else if (err?.response?.data?.detail) {
        errorMessage = err.response.data.detail;
      } else if (err?.code === 'ERR_NETWORK' || err?.message?.includes('Network Error') || err?.code === 'ECONNREFUSED') {
        errorMessage = 'Impossible de se connecter au backend sur le port 8000. Vérifiez que le backend est bien démarré.';
      } else if (err?.code === 'ECONNABORTED' || err?.message?.includes('timeout')) {
        errorMessage = 'La requête a pris trop de temps. Le backend semble surchargé ou lent.';
      }
      
      setError(errorMessage);
    } finally {
      setUploading(false);
    }
  };

  const handleCancel = () => {
    setSelectedFile(null);
    setClassification(null);
    setShowDomainSelector(false);
    setTargetDomain(currentDomain);
    setError(null);
    setSuccess(false);
    setProgress(0);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-4">
      {/* Zone de drag & drop */}
      {!selectedFile && (
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
            dragActive
              ? 'border-primary-500 bg-primary-50'
              : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleFileSelect}
            className="hidden"
            accept=".pdf,.doc,.docx,.txt,.md"
          />
          <div className="space-y-2">
            <span className="text-4xl">📄</span>
            <p className="text-gray-600">
              Glissez vos fichiers ici ou{' '}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="text-primary-600 hover:text-primary-700 underline"
              >
                cliquez pour sélectionner
              </button>
            </p>
            <p className="text-xs text-gray-500">
              Formats supportés: PDF, DOC, DOCX, TXT, MD (max 50MB)
            </p>
          </div>
        </div>
      )}

      {/* Fichier sélectionné */}
      {selectedFile && !success && (
        <div className="space-y-4">
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <span className="text-2xl">📄</span>
                <div>
                  <p className="font-medium text-gray-900">{selectedFile.name}</p>
                  <p className="text-sm text-gray-500">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={handleCancel}
                className="text-gray-400 hover:text-gray-600"
                disabled={uploading}
              >
                ✕
              </button>
            </div>
          </div>

          {/* Sélecteur de domaine */}
          {showDomainSelector && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                📍 Choisir le domaine de destination
              </label>
              <div className="relative">
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowDomainSelector(!showDomainSelector);
                  }}
                  className="w-full flex items-center justify-between gap-2 px-4 py-2.5 bg-white border border-gray-300 rounded-lg hover:border-gray-400 transition-colors text-left"
                >
                  <div className="flex items-center gap-2.5">
                    {(() => {
                      const domainConfig = getDomainConfig(targetDomain);
                      const DomainIcon = domainConfig.icon;
                      const domainClasses = getDomainClasses(targetDomain);
                      return (
                        <>
                          <DomainIcon className={`w-4 h-4 ${domainClasses.text}`} />
                          <span className="font-medium text-gray-900">{domainConfig.name}</span>
                          <span className="text-xs text-gray-500">({domainConfig.description})</span>
                        </>
                      );
                    })()}
                  </div>
                  <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${showDomainSelector ? 'rotate-180' : ''}`} />
                </button>
                
                {showDomainSelector && (
                  <>
                    <div 
                      className="fixed inset-0 z-10" 
                      onClick={() => setShowDomainSelector(false)}
                    />
                    <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-large border border-gray-200 z-20 overflow-hidden max-h-80 overflow-y-auto">
                      <div className="p-2">
                        {Object.values(domains).map((domain) => {
                          const DomainIcon = domain.icon;
                          const isSelected = domain.id === targetDomain;
                          const domainClasses = getDomainClasses(domain.id);
                          
                          return (
                            <button
                              key={domain.id}
                              onClick={() => {
                                console.log('[DocumentUploader] Domaine sélectionné:', domain.id);
                                setTargetDomain(domain.id);
                                setShowDomainSelector(false);
                              }}
                              className={`w-full flex items-center gap-3 px-3.5 py-3 rounded-lg 
                                transition-all duration-200 text-left group
                                ${isSelected 
                                  ? `${domainClasses.bgLight} ${domainClasses.text} shadow-soft` 
                                  : 'hover:bg-gray-50 text-gray-700'
                                }`}
                            >
                              <DomainIcon className={`w-4 h-4 flex-shrink-0 ${isSelected ? '' : 'text-gray-400 group-hover:text-gray-600'}`} />
                              <div className="flex-1 min-w-0">
                                <div className="font-medium text-sm">{domain.name}</div>
                                <div className="text-xs text-gray-500 truncate mt-0.5">{domain.description}</div>
                              </div>
                              {isSelected && (
                                <Check className="w-4 h-4 flex-shrink-0" />
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </>
                )}
              </div>
              <p className="text-xs text-gray-600 mt-2">
                Le document sera uploadé dans le domaine <strong>{getDomainConfig(targetDomain).name}</strong> (port {getDomainPort(targetDomain)})
              </p>
              <div className="mt-2 p-2 bg-white rounded border border-gray-200">
                <p className="text-xs font-mono text-gray-700">
                  Domaine sélectionné: <span className="font-bold text-blue-600">{targetDomain}</span>
                </p>
              </div>
            </div>
          )}

          {/* Classification preview (après upload) */}
          {classification && (
            <ClassificationPreview
              classification={classification}
              onDomainChange={(domain) => {
                setTargetDomain(domain);
              }}
              editable={classification.confidence < 0.7}
            />
          )}

          {/* Barre de progression */}
          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-sm text-gray-600">
                <span>Upload en cours...</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          {/* Actions */}
          {!uploading && (
            <div className="flex space-x-3">
              <button
                onClick={handleUpload}
                disabled={!targetDomain}
                className="flex-1 bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                <Upload className="w-4 h-4" />
                {classification ? 'Confirmer et uploader' : `Uploader dans ${getDomainConfig(targetDomain).name}`}
              </button>
              <button
                onClick={handleCancel}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Annuler
              </button>
            </div>
          )}

          {/* Erreur */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>
      )}

      {/* Succès */}
      {success && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <p className="text-green-700 font-medium">
            ✓ Document uploadé avec succès !
          </p>
          {classification && (
            <p className="text-sm text-green-600 mt-1">
              Classifié dans le domaine: {classification.domain}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

