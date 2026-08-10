export const ISOLATED_TAGS = new Set([
  "@umm", "@uhh", "@hmm", "@ugh", "@huh", "@tsk", "@uh-huh", "@ehh",
  "@stutter-block", "@silence", "@unintelligible",
  "@laughter", "@cry", "@hum", "@breathe", "@sniff", "@nose-blowing",
  "@cough", "@sneeze", "@throat-clearing", "@yawn", "@eating-sounds",
  "@snore", "@groan", "@sigh",
]);

export const SPAN_TAGS = new Set([
  "filler", "repetition", "broken-word", "repair", "false-start", "prolongation",
  "crying", "yelling", "laughing", "singing", "humming", "whistling", "whispering",
  "emphasis", "falling-pitch", "raising-pitch",
]);

export const NER_TYPES = new Set([
  "PER", "GPE", "FAC", "LOC", "ITEM", "WOA", "EVENT", "SPORTS", "ORG",
  "BRAND", "HON", "DATETIME", "MONEY", "QUANT", "NUM", "LANG", "LAW", "ID",
]);

export const LANGUAGE_CODES = new Set([
  "en", "hi", "bn", "mr", "te", "ta", "gu", "ur", "kn", "or", 
  "ml", "pa", "as", "mai", "sat", "ks", "ne", "sd", "doi", 
  "kok", "mni", "brx", "sa"
]);

export interface Token {
  type: 'TEXT' | 'TAG';
  value: string;
  start: number;
  end: number;
}

export const TOKEN_PATTERN = /(@[A-Za-z0-9\-]+)|(&[A-Za-z0-9\-]+)|(\#[A-Za-z]*\[[^\]]+\]\([^)]+\))|(\![A-Za-z]*\[[^\]]+\]\([^)]+\))|(\$[A-Za-z\-]*\[[^\]]+\]\([^)]+\))|(\[[^\]]+\]\([^)]+\))/g;

export function tokenize(text: string): Token[] {
  const tokens: Token[] = [];
  let index = 0;
  
  let match;
  TOKEN_PATTERN.lastIndex = 0;
  while ((match = TOKEN_PATTERN.exec(text)) !== null) {
    if (match.index > index) {
      tokens.push({
        type: 'TEXT',
        value: text.slice(index, match.index),
        start: index,
        end: match.index,
      });
    }
    
    tokens.push({
      type: 'TAG',
      value: match[0],
      start: match.index,
      end: TOKEN_PATTERN.lastIndex,
    });
    
    index = TOKEN_PATTERN.lastIndex;
  }
  
  if (index < text.length) {
    tokens.push({
      type: 'TEXT',
      value: text.slice(index),
      start: index,
      end: text.length,
    });
  }
  
  return tokens;
}

export type ASTNode = 
  | { type: 'TEXT'; text: string }
  | { type: 'ISOLATED'; tag: string }
  | { type: 'SPAN_START'; tag: string }
  | { type: 'SPAN_END'; tag: string }
  | { type: 'BRACKET'; category: string; subtype: string | null; verbatim: string; normalized: string };

const BRACKET_PATTERN = /^([!#$]?[A-Za-z\-]*)\[([^\]]+)\]\(([^)]+)\)$/;

export function parseToken(token: Token): ASTNode {
  if (token.type === 'TEXT') {
    return { type: 'TEXT', text: token.value };
  }
  
  const value = token.value;
  
  if (ISOLATED_TAGS.has(value)) {
    return { type: 'ISOLATED', tag: value };
  }
  
  if (value.endsWith('-start')) {
    return { type: 'SPAN_START', tag: value.slice(1, -6) };
  }
  
  if (value.endsWith('-end')) {
    return { type: 'SPAN_END', tag: value.slice(1, -4) };
  }
  
  const match = value.match(BRACKET_PATTERN);
  if (match) {
    let prefix = match[1] || '';
    const verbatim = match[2];
    const normalized = match[3];
    
    let category = 'NORMAL';
    let subtype = null;
    
    if (prefix.startsWith('!')) {
      category = 'CODE';
      subtype = prefix.slice(1) || null;
    } else if (prefix.startsWith('#')) {
      category = 'NER';
      subtype = prefix.slice(1) || null;
    } else if (prefix.startsWith('$')) {
      category = 'ACCENT';
      subtype = prefix.slice(1) || null;
    }
    
    return { type: 'BRACKET', category, subtype, verbatim, normalized };
  }
  
  throw new Error(`Unknown RSML token: ${token.value}`);
}

export function parse(tokens: Token[]): ASTNode[] {
  return tokens.map(parseToken);
}

export function normalizeNode(node: ASTNode): string {
  if (node.type === 'TEXT') return node.text;
  if (node.type === 'ISOLATED') return '';
  if (node.type === 'SPAN_START') return '';
  if (node.type === 'SPAN_END') return '';
  if (node.type === 'BRACKET') return node.normalized;
  return '';
}

export function normalize(ast: ASTNode[]): string {
  let output = ast.map(normalizeNode).join('');
  output = output.replace(/\s+/g, ' ');
  output = output.replace(/\s+([.,!?;:])/g, '$1');
  return output.trim();
}

export function validate(ast: ASTNode[]): string[] {
  const messages: string[] = [];
  
  // validate spans
  const stack: string[] = [];
  for (const node of ast) {
    if (node.type === 'SPAN_START') {
      const isSpeaker = node.tag.startsWith('s') && !isNaN(Number(node.tag.slice(1)));
      if (!isSpeaker && !SPAN_TAGS.has(node.tag)) {
        messages.push(`ERROR: Unknown span tag '${node.tag}'`);
      }
      stack.push(node.tag);
    } else if (node.type === 'SPAN_END') {
      if (stack.length === 0) {
        messages.push(`ERROR: Unexpected closing tag '${node.tag}'`);
        continue;
      }
      const current = stack.pop();
      if (current !== node.tag) {
        messages.push(`ERROR: Mismatched span '${current}' and '${node.tag}'`);
      }
    }
  }
  while (stack.length > 0) {
    const tag = stack.pop();
    messages.push(`ERROR: Unclosed span '${tag}'`);
  }
  
  let previousIsolated: string | null = null;
  
  for (const node of ast) {
    if (node.type === 'BRACKET') {
      if (node.category === 'NER') {
        if (!node.subtype) {
          messages.push("ERROR: NER annotation missing entity type.");
        } else if (!NER_TYPES.has(node.subtype)) {
          messages.push(`ERROR: Invalid NER type '${node.subtype}'`);
        }
      }
      if (node.category === 'CODE') {
        if (!node.subtype) {
          messages.push("ERROR: Code-mixing annotation missing language code.");
        } else if (!LANGUAGE_CODES.has(node.subtype)) {
          messages.push(`ERROR: Invalid language code '${node.subtype}'`);
        }
      }
      if (node.verbatim.trim() === '') messages.push("WARNING: Empty verbatim text.");
      if (node.normalized.trim() === '') messages.push("WARNING: Empty normalized text.");
    }
    
    if (node.type === 'ISOLATED') {
      if (previousIsolated === node.tag) {
        messages.push(`WARNING: Repeated isolated tag '${node.tag}'`);
      }
      previousIsolated = node.tag;
    } else {
      previousIsolated = null;
    }
  }
  
  const hasTextOrTag = ast.some(node => 
    (node.type === 'TEXT' && node.text.trim().length > 0) ||
    node.type === 'ISOLATED' ||
    node.type === 'SPAN_START' ||
    node.type === 'SPAN_END' ||
    node.type === 'BRACKET'
  );
  if (!hasTextOrTag) {
    messages.push("ERROR: Transcript contains no text or tags.");
  }
  
  return messages;
}

export function processRSML(text: string | undefined | null): { normalized: string; errors: string[] } {
  if (text === undefined || text === null) {
    return { normalized: '', errors: [] };
  }
  try {
    const tokens = tokenize(text);
    const ast = parse(tokens);
    const errors = validate(ast);
    const normalized = normalize(ast);
    return { normalized, errors };
  } catch (e: any) {
    return { normalized: '', errors: [e.message] };
  }
}
