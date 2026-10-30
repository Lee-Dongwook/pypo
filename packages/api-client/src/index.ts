/**
 * Typed client for the card allocation API.
 *
 * Types mirror the Pydantic models in `src/app/card/schemas.py`. When a field
 * moves there, it moves here too; there is no code generation yet.
 */

export type Tier = {
  spend_threshold: number
  discount_cap: number
  clause: string
}

export type Card = {
  card_id: string
  name: string
  issuer: string
  tiers: Tier[]
  as_of: string
  excluded_spend_note: string
}

export type Catalog = {
  as_of: string
  note: string
  cards: Card[]
}

export type AdviceAction = "fill" | "skip"

export type AdviceReason =
  | "reachable"
  | "over_budget"
  | "lower_priority"
  | "no_gain"
  | "top_tier"

export type CardAdvice = {
  card_id: string
  name: string
  recognized_spend: number
  current_cap: number
  next_threshold: number | null
  gap: number | null
  incremental_cap: number
  action: AdviceAction
  reason: AdviceReason
}

export type AllocationPlan = {
  planned_spend: number
  advice: CardAdvice[]
  total_gain: number
  usage: number
  leftover: number
}

export type PlanInput = {
  spends: Record<string, number>
  planned_spend: number
}

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

const DEFAULT_BASE_URL = "/api"

async function request<T>(path: string, init: RequestInit = {}, baseUrl = DEFAULT_BASE_URL): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { "content-type": "application/json", ...init.headers },
  })

  if (!response.ok) {
    let message = `요청이 실패했습니다 (${response.status})`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === "string") message = body.detail
      else if (Array.isArray(body.detail)) message = "입력값을 확인해 주세요"
    } catch {
      // 응답 본문이 JSON이 아니면 기본 문구를 쓴다.
    }
    throw new ApiError(message, response.status)
  }

  return (await response.json()) as T
}

export function fetchCatalog(baseUrl?: string): Promise<Catalog> {
  return request<Catalog>("/card/products", { cache: "no-store" }, baseUrl)
}

export function createPlan(input: PlanInput, baseUrl?: string): Promise<AllocationPlan> {
  return request<AllocationPlan>("/card/plan", { method: "POST", body: JSON.stringify(input) }, baseUrl)
}

export function formatWon(value: number): string {
  return `${value.toLocaleString("ko-KR")}원`
}
