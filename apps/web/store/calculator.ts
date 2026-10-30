import type { AllocationPlan } from "@pypo/api-client";
import { create } from "zustand";

type CalculatorState = {
  /** 등록한 카드 ID → 이번 달 실적 인정 금액. null은 "아직 모름"이라 계산에서 뺀다. 0은 "안 씀"이다. */
  myCards: Record<string, number | null>;
  plannedSpend: number | null;
  plan: AllocationPlan | null;
  addCard: (cardId: string) => void;
  removeCard: (cardId: string) => void;
  setSpend: (cardId: string, amount: number | null) => void;
  setPlannedSpend: (amount: number | null) => void;
  setPlan: (plan: AllocationPlan | null) => void;
};

export const useCalculator = create<CalculatorState>()((set) => ({
  myCards: {},
  plannedSpend: null,
  plan: null,
  addCard: (cardId) => set((state) => ({ myCards: { ...state.myCards, [cardId]: null } })),
  removeCard: (cardId) =>
    set((state) => ({
      myCards: Object.fromEntries(Object.entries(state.myCards).filter(([id]) => id !== cardId)),
    })),
  setSpend: (cardId, amount) => set((state) => ({ myCards: { ...state.myCards, [cardId]: amount } })),
  setPlannedSpend: (plannedSpend) => set({ plannedSpend }),
  setPlan: (plan) => set({ plan }),
}));
