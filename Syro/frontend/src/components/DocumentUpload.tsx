import { useState, useRef } from 'react';
import { Upload, File, X, CheckCircle, Loader2 } from 'lucide-react';
import { documentService } from '../services/api';

interface DocumentUploadProps {
  onUploadComplete?: () => void;
  currentDomain?: string;
}

interface UploadedFile {
  id: string;
  name: string;
  status: 'uploading' | 'success' | 'error';
  error?: string;
}

export default function DocumentUpload({ onUploadComplete, currentDomain = 'general' }: DocumentUploadProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = async (selectedFiles: FileList | null) => {
    if (!selectedFiles || selectedFiles.length === 0) return;

    const newFiles: UploadedFile[] = Array.from(selectedFiles).map(file => ({
      id: Date.now().toString() + Math.random(),
      name: file.name,
      status: 'uploading' as const,
    }));

    setFiles(prev => [...prev, ...newFiles]);

    // Upload chaque fichier
    for (let i = 0; i < selectedFiles.length; i++) {
      const file = selectedFiles[i];
      const fileId = newFiles[i].id;

      try {
        const formData = new FormData();
        formData.append('file', file);

        await documentService.uploadFile(file, undefined, currentDomain);

        setFiles(prev =>
          prev.map(f =>
            f.id === fileId
              ? { ...f, status: 'success' as const }
              : f
          )
        );

        onUploadComplete?.();
      } catch (error: any) {
        setFiles(prev =>
          prev.map(f =>
            f.id === fileId
              ? { ...f, status: 'error' as const, error: error.message || 'Erreur lors de l\'upload' }
              : f
          )
        );
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  return (
    <div className="space-y-4">
      <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
        Documents
      </h3>

      {/* Zone de drag & drop */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
          isDragging
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 hover:border-gray-400 hover:bg-gray-50'
        }`}
      >
        <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
        <p className="text-sm font-medium text-gray-700 mb-1">
          Glissez vos documents ici
        </p>
        <p className="text-xs text-gray-500">
          ou cliquez pour sélectionner
        </p>
        <p className="text-xs text-gray-400 mt-2">
          PDF, DOCX, TXT (max 10MB)
        </p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.txt,.md"
          onChange={(e) => handleFileSelect(e.target.files)}
          className="hidden"
        />
      </div>

      {/* Liste des fichiers uploadés */}
      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200"
            >
              <File className="w-4 h-4 text-gray-400 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-medium text-gray-700 truncate">
                  {file.name}
                </div>
                {file.error && (
                  <div className="text-xs text-red-600 mt-0.5">{file.error}</div>
                )}
              </div>
              {file.status === 'uploading' && (
                <Loader2 className="w-4 h-4 text-gray-400 animate-spin flex-shrink-0" />
              )}
              {file.status === 'success' && (
                <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
              )}
              {file.status === 'error' && (
                <button
                  onClick={() => removeFile(file.id)}
                  className="p-1 rounded hover:bg-gray-200 transition-colors"
                >
                  <X className="w-4 h-4 text-red-600" />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

