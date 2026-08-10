import React, { useState, useEffect, useRef, useMemo } from 'react';
import { processRSML } from '../../utils/rsml';
import { AlertCircle } from 'lucide-react';

interface RSMLSegmentEditorProps {
  value: string;
  onChange: (val: string) => void;
  disabled: boolean;
  readOnly?: boolean;
}

const rsmlTags = [
  "breathe", "broken-word-end", "broken-word-start", "cough", "cry",
  "crying-end", "crying-start", "eating-sounds", "ehh", "emphasis-end", 
  "emphasis-start", "falling-pitch-end", "falling-pitch-start", "false-start-end", "false-start-start", 
  "filler-end", "filler-start", "groan", "hmm", "huh",
  "hum", "humming-end", "humming-start", "laughing-end", "laughing-start",
  "laughter", "nose-blowing", "prolongation-end", "prolongation-start", "raising-pitch-end",
  "raising-pitch-start", "repair-end", "repair-start", "repetition-end", "repetition-start",
  "sigh", "silence", "singing-end", "singing-start", "sneeze",
  "sniff", "snore", "stutter-block", "throat-clearing", "tsk",
  "ugh", "uh-huh", "uhh", "umm", "unintelligible",
  "whispering-end", "whispering-start", "whistling-end", "whistling-start", "yawn", 
  "yelling-end", "yelling-start"
];

export function RSMLSegmentEditor({ value, onChange, disabled, readOnly = false }: RSMLSegmentEditorProps) {
  const { errors } = useMemo(() => processRSML(value), [value]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const isEditorDisabled = disabled || readOnly;

  // Autocomplete popup state
  const [showPopup, setShowPopup] = useState(false);
  const [query, setQuery] = useState('');
  const [tagMatchRange, setTagMatchRange] = useState<{ start: number; end: number } | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Filter tags by query
  const filteredTags = useMemo(() => {
    if (!query) return rsmlTags;
    const q = query.toLowerCase();
    return rsmlTags.filter(t => t.toLowerCase().includes(q));
  }, [query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [filteredTags]);

  const insertTag = (tag: string) => {
    if (isEditorDisabled || !textareaRef.current || !tagMatchRange) return;
    const el = textareaRef.current;
    const before = value.substring(0, tagMatchRange.start);
    const after = value.substring(tagMatchRange.end);
    const inserted = `@${tag} `;
    const newValue = before + inserted + after;
    
    onChange(newValue);
    setShowPopup(false);

    // Set focus and cursor position past the inserted tag
    setTimeout(() => {
      if (el) {
        el.focus();
        const newCursor = before.length + inserted.length;
        el.setSelectionRange(newCursor, newCursor);
      }
    }, 0);
  };

  const handleSelection = (e: React.SyntheticEvent<HTMLTextAreaElement>) => {
    if (isEditorDisabled) return;
    const el = e.currentTarget;
    const cursorPos = el.selectionStart;
    const textBefore = value.substring(0, cursorPos);
    
    // Search backwards for the last '@'
    const atIndex = textBefore.lastIndexOf('@');
    if (atIndex !== -1) {
      const tagQuery = textBefore.substring(atIndex + 1);
      if (!/\s/.test(tagQuery)) {
        setQuery(tagQuery);
        setTagMatchRange({ start: atIndex, end: cursorPos });
        setShowPopup(true);
        return;
      }
    }
    setShowPopup(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (isEditorDisabled || !showPopup || filteredTags.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % filteredTags.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filteredTags.length) % filteredTags.length);
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      insertTag(filteredTags[selectedIndex]);
    } else if (e.key === 'Escape') {
      setShowPopup(false);
    }
  };

  // Auto-expand textarea height dynamically as content grows
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.max(80, textareaRef.current.scrollHeight)}px`;
    }
  }, [value]);

  return (
    <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          if (!isEditorDisabled) {
            onChange(e.target.value);
            handleSelection(e);
          }
        }}
        onClick={handleSelection}
        onKeyUp={handleSelection}
        onKeyDown={handleKeyDown}
        disabled={isEditorDisabled}
        readOnly={isEditorDisabled}
        className="input-field"
        style={{
          minHeight: '80px',
          overflowY: 'hidden',
          resize: 'none',
          fontFamily: 'var(--font-sans)',
          lineHeight: '1.5',
          opacity: disabled ? 0.7 : 1,
          borderColor: errors.length > 0 && !disabled ? '#ef4444' : 'var(--border-solid)'
        }}
        placeholder="Enter RSML transcript here..."
      />

      {/* VS Code Intellisense Style Autocomplete Dropdown */}
      {showPopup && filteredTags.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '90px',
          left: '10px',
          zIndex: 1000,
          width: '260px',
          maxHeight: '200px',
          overflowY: 'auto',
          background: '#181825',
          border: '1px solid #45475a',
          borderRadius: '6px',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.6)',
          padding: '4px 0',
          fontFamily: 'monospace',
          fontSize: '0.85rem',
        }}>
          {filteredTags.map((tag, i) => {
            const isSelected = i === selectedIndex;
            return (
              <div
                key={tag}
                onMouseDown={(e) => {
                  e.preventDefault(); // Prevents textarea blur so click works 100%!
                  insertTag(tag);
                }}
                onMouseEnter={() => setSelectedIndex(i)}
                style={{
                  padding: '6px 12px',
                  cursor: 'pointer',
                  background: isSelected ? '#585b70' : 'transparent',
                  color: isSelected ? '#ffffff' : '#cdd6f4',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                <span style={{ color: '#cba6f7', fontSize: '0.75rem' }}>🏷️</span>
                <span>{tag}</span>
              </div>
            );
          })}
        </div>
      )}

      {errors.length > 0 && !disabled && (
        <div style={{ 
          background: 'rgba(239, 68, 68, 0.1)', 
          border: '1px solid rgba(239, 68, 68, 0.3)',
          borderRadius: 'var(--radius-md)',
          padding: '0.5rem',
          display: 'flex',
          flexDirection: 'column',
          gap: '0.25rem'
        }}>
          {errors.map((err, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem', color: '#ef4444', fontSize: '0.8rem' }}>
              <AlertCircle size={14} style={{ flexShrink: 0, marginTop: '0.1rem' }} />
              <span>{err}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
