import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { datasetsApi } from '../../services/api';
import { formatDurationHoursMins, formatDateIndian } from '../../utils/time';

export default function DatasetsManagement() {
  const queryClient = useQueryClient();
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [expandedDatasetId, setExpandedDatasetId] = useState<string | null>(null);
  const [uploadData, setUploadData] = useState<{
    zipFile: File | null;
    language: string;
  }>({
    zipFile: null,
    language: 'English',
  });

  const { data: datasets, isLoading, error } = useQuery({
    queryKey: ['datasets'],
    queryFn: datasetsApi.getAll,
  });

  const deleteMutation = useMutation({
    mutationFn: datasetsApi.delete,
    onSuccess: () => {
      toast.success('Dataset deleted successfully');
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: () => {
      toast.error('Failed to delete dataset');
    }
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!uploadData.zipFile) {
        throw new Error('Please select a ZIP file');
      }
      const formData = new FormData();
      formData.append('dataset_file', uploadData.zipFile);
      formData.append('language', uploadData.language);
      return await datasetsApi.upload(formData);
    },
    onSuccess: (data: any) => {
      toast.success(data.message || 'Dataset uploaded successfully');
      setIsUploadModalOpen(false);
      setUploadData({ zipFile: null, language: 'English' });
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || err.message || 'Failed to upload dataset');
    }
  });

  if (isLoading) return <div style={{ padding: '2rem' }}>Loading datasets...</div>;
  if (error) return <div style={{ padding: '2rem', color: 'red' }}>Error loading datasets</div>;

  return (
    <div className="card glass-panel" style={{ minHeight: '600px', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.25rem', margin: 0 }}>Datasets</h2>
        <button 
          className="btn btn-primary" 
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          onClick={() => setIsUploadModalOpen(true)}
        >
          Upload Dataset (ZIP)
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-glass)', color: 'var(--text-muted)' }}>
              <th style={{ padding: '1rem' }}>Dataset Name</th>
              <th style={{ padding: '1rem' }}>Language</th>
              <th style={{ padding: '1rem' }}>Total Files</th>
              <th style={{ padding: '1rem' }}>Duration</th>
              <th style={{ padding: '1rem' }}>Uploaded By</th>
              <th style={{ padding: '1rem' }}>Date</th>
              <th style={{ padding: '1rem' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {datasets?.map((ds: any) => {
              const isExpanded = expandedDatasetId === ds.id;
              return (
                <React.Fragment key={ds.id}>
                  <tr style={{ borderBottom: isExpanded ? 'none' : '1px solid var(--border-glass)' }}>
                    <td style={{ padding: '1rem', fontWeight: 600 }}>
                      <button
                        onClick={() => setExpandedDatasetId(isExpanded ? null : ds.id)}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-main)',
                          font: 'inherit',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          padding: 0
                        }}
                      >
                        <span>{ds.name}</span>
                        <span style={{ fontSize: '0.75rem', color: '#818cf8' }}>
                          {isExpanded ? '▲' : '▼'}
                        </span>
                      </button>
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <span style={{
                        background: 'rgba(99, 102, 241, 0.2)',
                        color: '#818cf8',
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.75rem'
                      }}>
                        {ds.language}
                      </span>
                    </td>
                    <td style={{ padding: '1rem' }}>{ds.total_files}</td>
                    <td style={{ padding: '1rem' }}>{formatDurationHoursMins(ds.total_duration)}</td>
                    <td style={{ padding: '1rem', color: 'var(--text-main)', fontWeight: 500 }}>
                      {ds.uploader_username || ds.uploaded_by || 'Admin'}
                    </td>
                    <td style={{ padding: '1rem', color: 'var(--text-muted)' }}>
                      {formatDateIndian(ds.uploaded_at)}
                    </td>
                    <td style={{ padding: '1rem' }}>
                      <button 
                        className="btn btn-secondary" 
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: '#ef4444', borderColor: 'rgba(239, 68, 68, 0.3)' }}
                        onClick={() => {
                          if(window.confirm('Are you sure you want to delete this dataset? This will permanently delete all associated audio files and annotations.')) {
                            deleteMutation.mutate(ds.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr style={{ borderBottom: '1px solid var(--border-glass)', background: 'rgba(15, 23, 42, 0.3)' }}>
                      <td colSpan={7} style={{ padding: '1rem 1.5rem' }}>
                        <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--primary-main)', marginBottom: '0.75rem' }}>
                          Mapped File List ({ds.mapped_files?.length || 0} items)
                        </div>
                        {(!ds.mapped_files || ds.mapped_files.length === 0) ? (
                          <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>No audio-transcript mappings found.</div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxWidth: '850px' }}>
                            {ds.mapped_files.map((mf: any, idx: number) => (
                              <div 
                                key={idx} 
                                style={{ 
                                  display: 'grid', 
                                  gridTemplateColumns: '1fr 100px 1fr', 
                                  alignItems: 'center', 
                                  gap: '1rem', 
                                  padding: '0.4rem 0.75rem',
                                  background: 'rgba(0, 0, 0, 0.2)',
                                  borderRadius: '6px',
                                  border: '1px solid rgba(255, 255, 255, 0.05)',
                                  fontFamily: 'monospace', 
                                  fontSize: '0.85rem' 
                                }}
                              >
                                {/* Left: Audio Filename + Duration */}
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                                  <span style={{ color: '#38bdf8', fontWeight: 600 }}>{mf.audio_filename}</span>
                                  <span style={{
                                    fontSize: '0.75rem',
                                    color: '#cbd5e1',
                                    background: 'rgba(148, 163, 184, 0.15)',
                                    padding: '0.15rem 0.5rem',
                                    borderRadius: '4px',
                                    fontFamily: 'var(--font-sans)',
                                    fontWeight: 500,
                                    whiteSpace: 'nowrap'
                                  }}>
                                    ⏱️ {formatDurationHoursMins(mf.duration)}
                                  </span>
                                </div>

                                {/* Center: Equal/Centered Arrow */}
                                <div style={{ color: '#64748b', textAlign: 'center', userSelect: 'none', fontSize: '0.85rem' }}>
                                  ───────►
                                </div>

                                {/* Right: Mapped Transcript JSON */}
                                <div style={{ color: '#34d399', fontWeight: 600, textAlign: 'left' }}>
                                  {mf.transcript_filename}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      {isUploadModalOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div className="card glass-panel" style={{ width: '400px', maxWidth: '90%', padding: '2rem' }}>
            <h3 style={{ margin: '0 0 1.5rem 0' }}>Upload Dataset</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem', fontWeight: 600 }}>Dataset Archive (ZIP)</label>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                  Include all audio files (.wav) and corresponding transcript JSON files (.json) mapped by ID inside this ZIP archive.
                </div>
                <input 
                  type="file" 
                  accept=".zip"
                  onChange={(e) => setUploadData(prev => ({ ...prev, zipFile: e.target.files?.[0] || null }))}
                  style={{
                    width: '100%',
                    padding: '0.5rem',
                    background: 'rgba(15, 23, 42, 0.4)',
                    border: '1px solid var(--border-glass)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-main)',
                  }}
                />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Language</label>
                <select 
                  value={uploadData.language}
                  onChange={(e) => setUploadData(prev => ({ ...prev, language: e.target.value }))}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    background: 'rgba(15, 23, 42, 0.4)',
                    border: '1px solid var(--border-glass)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-main)',
                    outline: 'none',
                  }}
                >
                  <option value="English">English</option>
                  <option value="Hindi">Hindi</option>
                  <option value="Telugu">Telugu</option>
                </select>
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                <button 
                  className="btn btn-secondary" 
                  onClick={() => setIsUploadModalOpen(false)}
                >
                  Cancel
                </button>
                <button 
                  className="btn btn-primary"
                  onClick={() => uploadMutation.mutate()}
                  disabled={uploadMutation.isPending || !uploadData.zipFile}
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Upload'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
