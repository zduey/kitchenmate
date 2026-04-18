import type {
  CreateShareResponse,
  SaveSharedRecipeResponse,
  SharedRecipeResponse,
} from "../types/sharing";

export class ShareError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = "ShareError";
    this.statusCode = statusCode;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ShareError(body.detail ?? res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

export async function createShare(recipeId: string): Promise<CreateShareResponse> {
  const res = await fetch(`/api/me/recipes/${encodeURIComponent(recipeId)}/share`, {
    method: "POST",
    credentials: "include",
  });
  return handleResponse<CreateShareResponse>(res);
}

export async function revokeShare(recipeId: string): Promise<void> {
  const res = await fetch(`/api/me/recipes/${encodeURIComponent(recipeId)}/share`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ShareError(body.detail ?? res.statusText, res.status);
  }
}

export async function getSharedRecipe(token: string): Promise<SharedRecipeResponse> {
  const res = await fetch(`/api/shared/${encodeURIComponent(token)}`);
  return handleResponse<SharedRecipeResponse>(res);
}

export async function saveSharedRecipe(token: string): Promise<SaveSharedRecipeResponse> {
  const res = await fetch(`/api/shared/${encodeURIComponent(token)}/save`, {
    method: "POST",
    credentials: "include",
  });
  return handleResponse<SaveSharedRecipeResponse>(res);
}
