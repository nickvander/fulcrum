export enum FieldType {
  TEXT = 'text',
  NUMBER = 'number',
  BOOLEAN = 'boolean',
  DATE = 'date',
}

export interface CustomField {
  id: number;
  name: string;
  type: FieldType;
}
