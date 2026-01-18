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

export type OutputFormat = "json" | "text" | "markdown" | "pdf" | "jpeg" | "png" | "webp" | "svg";

export interface ClipRequest {
  url: string;
  timeout?: number;
  use_llm_fallback?: boolean;
  force_llm?: boolean;
  force_refresh?: boolean;
}

export interface ClipResponse {
  recipe: Recipe;
  cached: boolean;
  content_changed: boolean | null;
}

export interface ConvertRequest {
  recipe: Recipe;
  format: Exclude<OutputFormat, "json">;
}

export interface ApiError {
  detail: string;
}
