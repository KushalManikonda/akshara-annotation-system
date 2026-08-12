// frontend/src/components/admin/ImportTranscriptModal.tsx
import { useState, useRef } from 'react';
import { api } from '../../services/api';
import toast from 'react-hot-toast';

interface ImportTranscriptModalProps {
  onClose: () => void;
  onSuccess: (data: any) => void;
}

type Language = 'hindi' | 'english' | 'telugu';

export default function ImportTranscriptModal({ onClose, onSuccess }: ImportTranscriptModalProps) {
  const [selectedLanguage, setSelectedLanguage] = useState<Language | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.name.endsWith('.json')) {
      setFile(dropped);
    } else {
      toast.error("Please drop a .json transcript file.");
    }
  };

  const handleSubmit = async () => {
    if (!selectedLanguage) {
      toast.error('Please select a language.');
      return;
    }
    if (!file) {
      toast.error('Please select a .json transcript file.');
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('transcript_file', file);
      formData.append('language', selectedLanguage);

      const res = await api.post('/curation/import-transcript', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(res.data.message || 'Transcript imported successfully.');
      onSuccess(res.data);
      onClose();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to import transcript.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0, 0, 0, 0.75)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 2000,
      padding: '1rem'
    }}>
      <div className="card glass-panel" style={{
        width: '100%',
        maxWidth: '520px',
        padding: '1.75rem',
        background: '#181825',
        border: '1px solid var(--border-glass)',
        boxShadow: '0 12px 32px rgba(0,0,0,0.7)',
        borderRadius: 'var(--radius-lg)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ margin: 0, fontSize: '1.125rem', fontWeight: 600 }}>Import Local Audio Transcript</h3>
          <button 
            onClick={onClose}
            disabled={isSubmitting}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
          >
            ✕
          </button>
        </div>

        <div style={{ marginBottom: '1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Import a JSON transcript directly into the annotation queue. 
          The WAV file is not uploaded; annotators will select it locally from their machine.
        </div>

        <div style={{ marginBottom: '1.25rem' }}>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            1. Target Language
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {(['hindi', 'english', 'telugu'] as Language[]).map(lang => (
              <button
                key={lang}
                type="button"
                className={`btn ${selectedLanguage === lang ? 'btn-primary' : 'btn-secondary'}`}
                style={{ flex: 1, textTransform: 'capitalize' }}
                onClick={() => setSelectedLanguage(lang)}
                disabled={isSubmitting}
              >
                {lang}
              </button>
            ))}
          </div>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, marginBottom: '0.5rem' }}>
            2. Transcript File (.json)
          </label>
          <div
            onDragEnter={(e) => e.preventDefault()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => !isSubmitting && fileInputRef.current?.click()}
            style={{
              border: '2px dashed var(--border-glass)',
              borderRadius: '0.5rem',
              padding: '1.5rem',
              textAlign: 'center',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              background: 'rgba(255,255,255,0.02)',
              color: file ? 'var(--color-primary)' : 'var(--text-muted)'
            }}
          >
            {file ? (
              <div style={{ fontWeight: 600 }}>✅ {file.name}</div>
            ) : (
              <div style={{ fontSize: '0.85rem' }}>Click or drop .json file here</div>
            )}
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) setFile(f);
            }}
          />
        </div>

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
          <button className="btn btn-secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={isSubmitting || !selectedLanguage || !file}>
            {isSubmitting ? 'Importing...' : 'Import to Queue'}
          </button>
        </div>
      </div>
    </div>
  );
}
