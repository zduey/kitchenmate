export interface Ingredient {
  name: string;
  amount?: string;
  unit?: string;
  preparation?: string;
  display_text?: string;
}

export interface RecipeMetadata {
  author?: string;
  servings?: string;
  prep_time?: number;
  cook_time?: number;
  total_time?: number;
  categories?: string[];
}

export interface Recipe {
  title: string;
  ingredients: Ingredient[];
  instructions: string[];
  source_url?: string;
  image?: string;
  metadata?: RecipeMetadata;
}

export type OutputFormat = "json" | "text" | "markdown";

export interface ClipRequest {
  url: string;
  format?: OutputFormat;
  timeout?: number;
  use_llm_fallback?: boolean;
  download?: boolean;
}

export interface ApiError {
  detail: string;
}
