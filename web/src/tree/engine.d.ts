// The skill-map engine is plain JavaScript (see engine.js).
export interface TreeIsland {id: string; title: string; format: string; url: string; minutes: number | null; club: boolean; goals: string[]}
export interface TreeOptions {fill?: boolean; module?: string | null; inset?: () => number; islands?: Record<string, TreeIsland[]>}
export function mountTree(root: HTMLElement, data: unknown, options?: TreeOptions): () => void;
