"use client";

import type { AllocationPlan, Card, CardAdvice } from "@pypo/api-client";
import { formatWon } from "@pypo/api-client";

const SKIP_LABEL: Record<string, string> = {
  lower_priority: "다른 카드가 더 이득입니다",
  no_gain: "구간이 올라가도 한도는 그대로입니다",
  top_tier: "이미 최고 구간입니다",
};

function FillRow({ item }: { item: CardAdvice }) {
  const nextCap = item.current_cap + item.incremental_cap;

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50/70 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold text-emerald-950">{item.name}에 쓰세요</p>
        <p className="shrink-0 text-sm font-semibold tabular-nums text-emerald-700">
          +{formatWon(item.incremental_cap)}
        </p>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-emerald-900/70">
        {formatWon(item.gap ?? 0)} 더 쓰면 {formatWon(item.next_threshold ?? 0)} 구간 · 한도{" "}
        {formatWon(item.current_cap)} → {formatWon(nextCap)}
      </p>
    </div>
  );
}

function HoldOffRow({ item }: { item: CardAdvice }) {
  return (
    <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-4">
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-sm font-semibold text-amber-950">{item.name}는 넘기지 마세요</p>
        <p className="shrink-0 text-xs tabular-nums text-amber-700">{formatWon(item.gap ?? 0)} 부족</p>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-amber-900/70">
        억지로 채우면 쓰지 않을 지출이 생깁니다. 다음 달에 자연스럽게 넘기는 편이 낫습니다.
      </p>
    </div>
  );
}

export function ResultPanel({
  plan,
  cards,
  onReset,
}: {
  plan: AllocationPlan;
  cards: Card[];
  onReset: () => void;
}) {
  const fills = plan.advice.filter((item) => item.action === "fill");
  const holdOffs = plan.advice.filter((item) => item.action === "skip" && item.reason === "over_budget");
  const rest = plan.advice.filter((item) => item.action === "skip" && item.reason !== "over_budget");

  return (
    <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
      <p className="text-xs font-medium tracking-wide text-zinc-400">늘어나는 한도</p>
      <p
        className={[
          "mt-1 text-3xl font-semibold tabular-nums",
          plan.total_gain > 0 ? "text-emerald-600" : "text-zinc-900",
        ].join(" ")}
      >
        {plan.total_gain > 0 ? `+${formatWon(plan.total_gain)}` : "0원"}
      </p>
      <p className="mt-2 text-xs text-zinc-500">
        남은 지출 {formatWon(plan.planned_spend)} 중 {formatWon(plan.usage)} 배분 · {formatWon(plan.leftover)} 남음
      </p>

      <div className="mt-5 space-y-2.5">
        {fills.map((item) => (
          <FillRow key={item.card_id} item={item} />
        ))}
        {holdOffs.map((item) => (
          <HoldOffRow key={item.card_id} item={item} />
        ))}
      </div>

      {fills.length === 0 ? (
        <p className="mt-4 rounded-xl bg-zinc-50 px-4 py-3 text-xs leading-relaxed text-zinc-500">
          이번 달 남은 지출로는 넘길 구간이 없습니다. 추가로 쓰지 않는 것이 이득입니다.
        </p>
      ) : null}

      {rest.length > 0 ? (
        <ul className="mt-4 space-y-1.5 border-t border-zinc-100 pt-4">
          {rest.map((item) => (
            <li key={item.card_id} className="flex items-baseline justify-between gap-3 text-xs text-zinc-500">
              <span className="truncate">{item.name}</span>
              <span className="shrink-0 text-zinc-400">{SKIP_LABEL[item.reason] ?? "이번 달은 넘기지 않습니다"}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <details className="mt-4 border-t border-zinc-100 pt-4">
        <summary className="cursor-pointer text-xs font-medium text-zinc-500">근거 조항 보기</summary>
        <ul className="mt-3 space-y-3">
          {plan.advice.map((item) => {
            const card = cards.find((candidate) => candidate.card_id === item.card_id);
            if (!card) return null;
            return (
              <li key={item.card_id} className="text-[11px] leading-relaxed text-zinc-500">
                <p className="font-medium text-zinc-600">
                  {card.name} · {card.issuer} · {card.as_of} 확인
                </p>
                <ul className="mt-1 space-y-0.5 text-zinc-400">
                  {card.tiers.map((tier) => (
                    <li key={tier.spend_threshold}>
                      {formatWon(tier.spend_threshold)} / {formatWon(tier.discount_cap)} — {tier.clause}
                    </li>
                  ))}
                </ul>
                {card.excluded_spend_note ? <p className="mt-1 text-zinc-400">{card.excluded_spend_note}</p> : null}
              </li>
            );
          })}
        </ul>
      </details>

      <p className="mt-4 rounded-lg bg-zinc-50 px-3 py-2.5 text-[11px] leading-relaxed text-zinc-500">
        한도는 상한입니다. 실제 할인은 그 카드로 결제한 만큼만 붙습니다. 최종 조건은 카드사 앱과 상품설명서를
        확인해 주세요.
      </p>

      <button
        type="button"
        onClick={onReset}
        className="mt-4 h-11 w-full rounded-xl border border-zinc-200 text-sm font-medium text-zinc-700 transition hover:bg-zinc-50 active:scale-[0.99]"
      >
        다시 계산
      </button>
    </section>
  );
}
