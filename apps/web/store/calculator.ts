import type { AllocationPlan } from "@pypo/api-client";
import { create } from "zustand";

type CalculatorState = {
  /** 카드 ID별 이번 달 실적 인정 금액. 0은 "모름"이 아니라 "안 씀"으로 본다. */
  spends: Record<string, number>;
  plannedSpend: number;
  plan: AllocationPlan | null;
  setSpend: (cardId: string, amount: number) => void;
  setPlannedSpend: (amount: number) => void;
  setPlan: (plan: AllocationPlan | null) => void;
  reset: () => void;
};

export const useCalculator = create<CalculatorState>()((set) => ({
  spends: {},
  plannedSpend: 0,
  plan: null,
  setSpend: (cardId, amount) =>
    set((state) => ({ spends: { ...state.spends, [cardId]: amount } })),
  setPlannedSpend: (plannedSpend) => set({ plannedSpend }),
  setPlan: (plan) => set({ plan }),
  reset: () => set({ spends: {}, plannedSpend: 0, plan: null }),
}));
