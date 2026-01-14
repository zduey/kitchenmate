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
  timeout?: number;
  use_llm_fallback?: boolean;
  force_llm?: boolean;
  stream?: boolean;
}

export interface ConvertRequest {
  recipe: Recipe;
  format: "text" | "markdown";
}

export interface ApiError {
  detail: string;
}

export type ClipStage = "fetching" | "parsing" | "llm" | "complete" | "error";

export interface ClipProgressEvent {
  stage: Exclude<ClipStage, "complete" | "error">;
  message: string;
}

export interface ClipCompleteEvent {
  stage: "complete";
  recipe: Recipe;
}

export interface ClipErrorEvent {
  stage: "error";
  message: string;
  status: number;
}

export type ClipStreamEvent = ClipProgressEvent | ClipCompleteEvent | ClipErrorEvent;
