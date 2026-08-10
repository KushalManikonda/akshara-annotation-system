import { useState } from 'react';

interface NormalizedPreviewProps {
  value: string;
}

interface ParsedNode {
  type: 'speaker' | 'span' | 'tag' | 'codemix' | 'number' | 'text';
  content: string;
  speakerNum?: string;
  category?: string;
  label?: string;
  bg?: string;
  color?: string;
  border?: string;
}

function getTagMeta(cleanTag: string) {
  const tag = cleanTag.toLowerCase();

  // Prosody
  if (tag.includes('pitch') || tag.includes('emphasis') || tag.includes('prolongation') || tag.includes('whispering') || tag.includes('singing') || tag.includes('yelling')) {
    const name = tag.replace(/-(start|end)$/, '').replace(/-/g, ' ');
    return { category: 'Prosody', label: `Prosody: ${name}`, bg: '#f3e8ff', color: '#6b21a8', border: '#c084fc' };
  }
  // Hesitation / Filler
  if (['umm', 'uhh', 'hmm', 'ugh', 'huh', 'tsk', 'uh-huh', 'ehh'].includes(tag) || tag.includes('filler')) {
    const name = tag.replace(/-(start|end)$/, '').replace(/-/g, ' ');
    return { category: 'Hesitation', label: `Hesitation: ${name}`, bg: '#fef9c3', color: '#854d0e', border: '#fde047' };
  }
  // Non-Verbal / Paralinguistic
  if (['laughter', 'cry', 'hum', 'breathe', 'sniff', 'nose-blowing', 'cough', 'sneeze', 'throat-clearing', 'yawn', 'eating-sounds', 'snore', 'groan', 'sigh'].includes(tag) || tag.includes('laugh') || tag.includes('crying') || tag.includes('humming')) {
    const name = tag.replace(/-(start|end)$/, '').replace(/-/g, ' ');
    return { category: 'Non-Verbal', label: `Non-Verbal: ${name}`, bg: '#dcfce7', color: '#166534', border: '#86efac' };
  }
  // Disfluency
  if (['stutter-block', 'silence', 'unintelligible'].includes(tag) || tag.includes('broken-word') || tag.includes('repetition') || tag.includes('repair') || tag.includes('false-start')) {
    const name = tag.replace(/-(start|end)$/, '').replace(/-/g, ' ');
    return { category: 'Disfluency', label: `Disfluency: ${name}`, bg: '#e0f2fe', color: '#075985', border: '#7dd3fc' };
  }

  const name = tag.replace(/-(start|end)$/, '').replace(/-/g, ' ');
  return { category: 'Tag', label: `Tag: ${name}`, bg: '#fef9c3', color: '#854d0e', border: '#fde047' };
}

function parseRSMLNodes(input: string): ParsedNode[] {
  if (!input) return [];

  // Suppress all speaker end tags (@s0-end, @s1-end, @s2-end, etc.)
  const text = input.replace(/@s\d+-end\b/gi, '');

  const nodes: ParsedNode[] = [];
  const rawTokens = text.split(/(\s+)/).filter(Boolean);

  let i = 0;
  while (i < rawTokens.length) {
    const token = rawTokens[i];

    if (/^\s+$/.test(token)) {
      nodes.push({ type: 'text', content: ' ' });
      i++;
      continue;
    }

    // Check Speaker Start Tag: @s1-start or @s1 or @s0-start
    const spkMatch = token.match(/^@s(\d+)(?:-start)?$/i);
    if (spkMatch) {
      nodes.push({
        type: 'speaker',
        content: `SPEAKER ${spkMatch[1]}:`,
        speakerNum: spkMatch[1],
      });
      i++;
      continue;
    }

    // Check Paired Span Start Tag: e.g. @raising-pitch-start ... @raising-pitch-end
    const spanStartMatch = token.match(/^@([a-z0-9-]+)-start$/i);
    if (spanStartMatch) {
      const tagName = spanStartMatch[1];
      const endTag = `@${tagName}-end`;

      // Look ahead for matching end tag
      let endIdx = -1;
      for (let j = i + 1; j < rawTokens.length; j++) {
        if (rawTokens[j].toLowerCase() === endTag.toLowerCase()) {
          endIdx = j;
          break;
        }
      }

      if (endIdx !== -1) {
        // Paired span found! Extract intermediate text
        const intermediate = rawTokens.slice(i + 1, endIdx).join('').trim();
        const meta = getTagMeta(tagName);
        nodes.push({
          type: 'span',
          content: intermediate || tagName,
          category: meta.category,
          label: meta.label,
          bg: meta.bg,
          color: meta.color,
          border: meta.border,
        });
        i = endIdx + 1;
        continue;
      }
    }

    // Single RSML Tag token (starts with @ or &)
    if (token.startsWith('@') || token.startsWith('&')) {
      const cleanTag = token.replace(/^[@&]/, '').replace(/-(start|end)$/, '');
      const meta = getTagMeta(cleanTag);
      nodes.push({
        type: 'tag',
        content: token,
        category: meta.category,
        label: meta.label,
        bg: meta.bg,
        color: meta.color,
        border: meta.border,
      });
      i++;
      continue;
    }

    // Code mixing [word:lang]
    if (token.startsWith('[') && token.endsWith(']')) {
      nodes.push({
        type: 'codemix',
        content: token.slice(1, -1),
        bg: '#ffedd5',
        color: '#c2410c',
        border: '#fdba74',
      });
      i++;
      continue;
    }

    // Numbers & Currency (e.g. ₹200, 2, 300)
    if (/^[₹$€£]?\d+/.test(token)) {
      nodes.push({
        type: 'number',
        content: token,
        bg: '#fef9c3',
        color: '#713f12',
        border: '#fde047',
      });
      i++;
      continue;
    }

    // Regular word
    nodes.push({ type: 'text', content: token });
    i++;
  }

  return nodes;
}

export function NormalizedPreview({ value }: NormalizedPreviewProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  if (!value || !value.trim()) {
    return <div style={{ minHeight: '36px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>Parsed RSML tag visualization will appear here...</div>;
  }

  const nodes = parseRSMLNodes(value);

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center', lineHeight: '2', fontSize: '0.9rem' }}>
        {nodes.map((node, idx) => {
          const isHovered = hoveredIndex === idx;

          // Speaker Badge (SPEAKER X:) -> Header pill + Line Break below
          if (node.type === 'speaker') {
            return (
              <div key={idx} style={{ flexBasis: '100%', display: 'flex', marginTop: idx === 0 ? 0 : '6px', marginBottom: '4px' }}>
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: '3px 12px',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    fontFamily: 'var(--font-sans)',
                    background: '#f8fafc',
                    color: '#4338ca',
                    border: '1.5px solid #c7d2fe',
                    letterSpacing: '0.04em',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                  }}
                >
                  {node.content}
                </span>
              </div>
            );
          }

          // Highlighted Span Node (text inside paired start/end tags)
          if (node.type === 'span') {
            return (
              <span
                key={idx}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                style={{
                  position: 'relative',
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '3px 12px',
                  borderRadius: '6px',
                  fontSize: '0.9rem',
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  background: node.bg,
                  color: node.color,
                  border: `1.5px solid ${node.border}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isHovered ? '0 2px 10px rgba(0,0,0,0.2)' : 'none',
                }}
              >
                {/* Tooltip on Hover */}
                {isHovered && (
                  <div style={{
                    position: 'absolute',
                    bottom: 'calc(100% + 8px)',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: '#18181b',
                    color: '#ffffff',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    boxShadow: '0 4px 14px rgba(0,0,0,0.5)',
                    zIndex: 1000,
                    pointerEvents: 'none',
                  }}>
                    {node.label}
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      left: '50%',
                      transform: 'translateX(-50%)',
                      width: 0,
                      height: 0,
                      borderLeft: '5px solid transparent',
                      borderRight: '5px solid transparent',
                      borderTop: '5px solid #18181b',
                    }} />
                  </div>
                )}
                {node.content}
              </span>
            );
          }

          // Single Tag Node (e.g. @umm, @laughter)
          if (node.type === 'tag') {
            return (
              <span
                key={idx}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                style={{
                  position: 'relative',
                  display: 'inline-flex',
                  alignItems: 'center',
                  padding: '3px 10px',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  fontFamily: 'monospace',
                  background: node.bg,
                  color: node.color,
                  border: `1.5px solid ${node.border}`,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  boxShadow: isHovered ? '0 2px 8px rgba(0,0,0,0.15)' : 'none',
                }}
              >
                {isHovered && (
                  <div style={{
                    position: 'absolute',
                    bottom: 'calc(100% + 8px)',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    background: '#18181b',
                    color: '#ffffff',
                    padding: '4px 10px',
                    borderRadius: '6px',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    boxShadow: '0 4px 14px rgba(0,0,0,0.5)',
                    zIndex: 1000,
                    pointerEvents: 'none',
                  }}>
                    {node.label}
                    <div style={{
                      position: 'absolute',
                      top: '100%',
                      left: '50%',
                      transform: 'translateX(-50%)',
                      width: 0,
                      height: 0,
                      borderLeft: '5px solid transparent',
                      borderRight: '5px solid transparent',
                      borderTop: '5px solid #18181b',
                    }} />
                  </div>
                )}
                {node.content}
              </span>
            );
          }

          // Code-mixing token [word:lang]
          if (node.type === 'codemix') {
            return (
              <span
                key={idx}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '3px 10px',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  background: node.bg,
                  color: node.color,
                  border: `1.5px solid ${node.border}`,
                }}
              >
                {node.content}
              </span>
            );
          }

          // Number token
          if (node.type === 'number') {
            return (
              <span
                key={idx}
                style={{
                  padding: '3px 10px',
                  borderRadius: '6px',
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  background: node.bg,
                  color: node.color,
                  border: `1.5px solid ${node.border}`,
                }}
              >
                {node.content}
              </span>
            );
          }

          // Regular word
          return <span key={idx} style={{ padding: '0 2px' }}>{node.content}</span>;
        })}
      </div>
  );
}
