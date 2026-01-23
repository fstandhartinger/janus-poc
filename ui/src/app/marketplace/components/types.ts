export type ComponentCategory = 'research' | 'coding' | 'memory' | 'tools' | 'models';
export type ComponentStatus = 'available' | 'coming_soon' | 'deprecated';

export interface ComponentReview {
  author: string;
  comment: string;
}

export interface ComponentContract {
  type: 'openapi' | 'mcp';
  url?: string;
  tools?: string[];
}

export interface Component {
  id: string;
  name: string;
  description: string;
  longDescription?: string;
  author: string;
  authorUrl?: string;
  category: ComponentCategory;
  icon?: string;
  thumbnail?: string;
  status: ComponentStatus;
  version: string;
  usageCount: number;
  rating?: number;
  contract: ComponentContract;
  integrationExample?: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
  totalCalls?: number;
  earnings?: number;
  versionHistory?: string[];
  reviews?: ComponentReview[];
}
