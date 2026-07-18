import type {
  AddMemberResponse,
  KitchenDetail,
  KitchenRecipe,
  KitchenSummary,
  ListKitchenRecipesResponse,
} from "../types/kitchen";
import type { UserRecipe } from "../types/recipe";

export class KitchenError extends Error {
  statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = "KitchenError";
    this.statusCode = statusCode;
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new KitchenError(body.detail ?? res.statusText, res.status);
  }
  return res.json() as Promise<T>;
}

export async function listKitchens(): Promise<KitchenSummary[]> {
  const res = await fetch("/api/kitchens", { credentials: "include" });
  return handleResponse<KitchenSummary[]>(res);
}

export async function getKitchen(kitchenId: string): Promise<KitchenDetail> {
  const res = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}`, {
    credentials: "include",
  });
  return handleResponse<KitchenDetail>(res);
}

export async function createKitchen(name: string): Promise<KitchenSummary> {
  const res = await fetch("/api/kitchens", {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  return handleResponse<KitchenSummary>(res);
}

export async function addMember(
  kitchenId: string,
  email: string
): Promise<AddMemberResponse> {
  const res = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}/members`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  return handleResponse<AddMemberResponse>(res);
}

export async function removeMember(kitchenId: string, userId: string): Promise<void> {
  const res = await fetch(
    `/api/kitchens/${encodeURIComponent(kitchenId)}/members/${encodeURIComponent(userId)}`,
    { method: "DELETE", credentials: "include" }
  );
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new KitchenError(body.detail ?? res.statusText, res.status);
  }
}

export async function shareRecipeToKitchen(
  kitchenId: string,
  userRecipeId: string
): Promise<KitchenRecipe> {
  const res = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}/recipes`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_recipe_id: userRecipeId }),
  });
  return handleResponse<KitchenRecipe>(res);
}

export async function listKitchenRecipes(
  kitchenId: string,
  cursor?: string,
  limit = 50
): Promise<ListKitchenRecipesResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  const res = await fetch(
    `/api/kitchens/${encodeURIComponent(kitchenId)}/recipes?${params}`,
    { credentials: "include" }
  );
  return handleResponse<ListKitchenRecipesResponse>(res);
}

export async function updateMemberRole(
  kitchenId: string,
  userId: string,
  role: "admin" | "member"
): Promise<void> {
  const res = await fetch(
    `/api/kitchens/${encodeURIComponent(kitchenId)}/members/${encodeURIComponent(userId)}`,
    {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    }
  );
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new KitchenError(body.detail ?? res.statusText, res.status);
  }
}

export async function getKitchenRecipe(
  kitchenId: string,
  kitchenRecipeId: string
): Promise<UserRecipe> {
  const res = await fetch(
    `/api/kitchens/${encodeURIComponent(kitchenId)}/recipes/${encodeURIComponent(kitchenRecipeId)}`,
    { credentials: "include" }
  );
  return handleResponse<UserRecipe>(res);
}

export async function removeKitchenRecipe(
  kitchenId: string,
  kitchenRecipeId: string
): Promise<void> {
  const res = await fetch(
    `/api/kitchens/${encodeURIComponent(kitchenId)}/recipes/${encodeURIComponent(kitchenRecipeId)}`,
    { method: "DELETE", credentials: "include" }
  );
  if (!res.ok && res.status !== 204) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new KitchenError(body.detail ?? res.statusText, res.status);
  }
}
