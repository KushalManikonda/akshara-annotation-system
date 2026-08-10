import {useState} from 'react';
import { ChevronDown, ChevronRight, HelpCircle } from 'lucide-react';

export function RSMLReference() {
  const [isOpen, setIsOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<'isolated' | 'spans' | 'ner' | 'lang'>('isolated');

  return (
    <div className="glass-panel" style={{ marginTop: '1rem', padding: '1rem' }}>
      <div 
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 500 }}>
          <HelpCircle size={16} className="text-primary" />
          RSML Tag Reference
        </div>
        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
      </div>

      {isOpen && (
        <div style={{ marginTop: '1rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            {(['isolated', 'spans', 'ner', 'lang'] as const).map(tab => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                style={{
                  background: activeTab === tab ? 'rgba(99, 102, 241, 0.2)' : 'transparent',
                  border: `1px solid ${activeTab === tab ? 'var(--color-primary)' : 'var(--border-solid)'}`,
                  color: activeTab === tab ? 'var(--text-main)' : 'var(--text-muted)',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                  cursor: 'pointer'
                }}
              >
                {tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxHeight: '200px', overflowY: 'auto', paddingRight: '0.5rem' }}>
            {activeTab === 'isolated' && (
              <div>
                <p><strong>Hesitations:</strong> <code>@umm, @uhh, @hmm, @ugh, @huh, @tsk, @uh-huh, @ehh</code></p>
                <p><strong>Paralinguistic sounds:</strong> <code>@laughter, @cry, @hum, @breathe, @sniff, @nose-blowing, @cough, @sneeze, @throat-clearing, @yawn, @eating-sounds, @snore, @groan, @sigh</code></p>
                <p><strong>Other:</strong> <code>@silence, @unintelligible, @stutter-block</code></p>
              </div>
            )}
            
            {activeTab === 'spans' && (
              <div>
                <p><strong>Disfluencies:</strong> <code>@name-start ... @name-end</code> (e.g. filler, repetition, broken-word, repair, false-start, prolongation)</p>
                <p><strong>Paralinguistics:</strong> <code>@crying-start ... @crying-end</code> (crying, yelling, laughing, singing, humming, whistling, whispering)</p>
                <p><strong>Prosody:</strong> emphasis, falling-pitch, raising-pitch</p>
                <p><strong>Speaker turns:</strong> <code>&s1-start ... &s1-end</code></p>
              </div>
            )}

            {activeTab === 'ner' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                <code>#PER[...](...)</code> - Person<br/>
                <code>#LOC[...](...)</code> - Location<br/>
                <code>#ORG[...](...)</code> - Organization<br/>
                <code>#GPE[...](...)</code> - Geo-political<br/>
                <code>#DATETIME[...](...)</code> - Date/Time<br/>
                <code>#MONEY[...](...)</code> - Money<br/>
              </div>
            )}

            {activeTab === 'lang' && (
              <div>
                <p><strong>Format:</strong> <code>!langcode[spoken](normalized)</code></p>
                <p><strong>Example:</strong> <code>!en[హలో](hello)</code></p>
                <p><strong>Codes:</strong> en, hi, bn, mr, te, ta, gu, ur, kn, or, ml, pa, as, mai, sat, ks, ne, sd, doi, kok, mni, brx, sa</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
