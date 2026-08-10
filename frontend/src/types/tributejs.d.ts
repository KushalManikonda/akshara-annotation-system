declare module 'tributejs' {
  export interface TributeOptions {
    values: Array<{key: string; value: string}>;
    selectTemplate?: (item: {original: {value: string}}) => string;
    noMatchTemplate?: () => string;
    requireLeadingSpace?: boolean;
    trigger?: string;
  }
  export default class Tribute {
    constructor(options: TributeOptions);
    attach(element: Element | NodeList | Element[]): void;
    detach(element: Element | NodeList | Element[]): void;
  }
}
