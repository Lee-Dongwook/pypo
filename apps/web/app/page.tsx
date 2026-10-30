"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { ApiError, createPlan, fetchCatalog } from "@pypo/api-client";

import { CardRow } from "@/components/card-row";
import { NumberField } from "@/components/number-field";
import { ResultPanel } from "@/components/result-panel";
import { useCalculator } from "@/store/calculator";

function StepLabel({ index, title, hint }: { index: number; title: string; hint: string }) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="flex h-5 w-5 items-center justify-center rounded-full bg-zinc-900 text-[11px] font-semibold text-white">
          {index}
        </span>
        <h2 className="text-sm font-semibold text-zinc-900">{title}</h2>
      </div>
      <p className="mt-2 text-[11px] leading-relaxed text-zinc-400">{hint}</p>
    </div>
  );
}

export default function Home() {
  const spends = useCalculator((state) => state.spends);
  const plannedSpend = useCalculator((state) => state.plannedSpend);
  const plan = useCalculator((state) => state.plan);
  const setSpend = useCalculator((state) => state.setSpend);
  const setPlannedSpend = useCalculator((state) => state.setPlannedSpend);
  const setPlan = useCalculator((state) => state.setPlan);
  const reset = useCalculator((state) => state.reset);

  const catalog = useQuery({ queryKey: ["card-catalog"], queryFn: () => fetchCatalog() });
  const mutation = useMutation({
    mutationFn: (input: Parameters<typeof createPlan>[0]) => createPlan(input),
    onSuccess: (result) => setPlan(result),
  });

  const cards = catalog.data?.cards ?? [];
  const canSubmit = plannedSpend > 0 && !mutation.isPending;

  return (
    <main className="mx-auto w-full max-w-md px-4 pb-16 pt-10">
      <header>
        <p className="text-[10px] font-semibold tracking-[0.22em] text-zinc-400">CARD PROBE</p>
        <h1 className="mt-2 text-[26px] font-semibold leading-tight tracking-tight text-zinc-900">
          이번 달 카드 배분
        </h1>
        <p className="mt-1.5 text-sm leading-relaxed text-zinc-500">
          남은 지출을 어디에 몰아야 다음 달 혜택 구간을 넘는지 계산합니다.
        </p>
        {catalog.data ? (
          <p className="mt-3 text-[11px] text-zinc-400">
            약관 기준일 {catalog.data.as_of.replace(/-/g, ". ")} · {cards.length}개 상품
          </p>
        ) : null}
      </header>

      {catalog.data?.note ? (
        <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50/70 px-3 py-2.5 text-[11px] leading-relaxed text-amber-900/80">
          {catalog.data.note}
        </p>
      ) : null}

      {catalog.isPending ? (
        <div className="mt-6 space-y-3">
          <div className="h-40 animate-pulse rounded-2xl bg-zinc-100" />
          <div className="h-28 animate-pulse rounded-2xl bg-zinc-100" />
        </div>
      ) : null}

      {catalog.isError ? (
        <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-5">
          <p className="text-sm font-medium text-zinc-900">카드 목록을 불러오지 못했습니다</p>
          <p className="mt-1 text-xs text-zinc-500">API 서버가 실행 중인지 확인해 주세요.</p>
          <button
            type="button"
            onClick={() => void catalog.refetch()}
            className="mt-4 h-10 w-full rounded-xl border border-zinc-200 text-sm font-medium text-zinc-700 hover:bg-zinc-50"
          >
            다시 시도
          </button>
        </div>
      ) : null}

      {plan ? (
        <div className="mt-6">
          <ResultPanel plan={plan} cards={cards} onReset={reset} />
        </div>
      ) : null}

      {catalog.isSuccess && !plan ? (
        <form
          className="mt-6 space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            if (!canSubmit) return;
            mutation.mutate({ spends, planned_spend: plannedSpend });
          }}
        >
          <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <StepLabel
              index={1}
              title="카드별 이번 달 실적"
              hint="카드사 앱에 표시된 '이번 달 실적' 숫자를 그대로 넣어 주세요. 총 사용액과 다릅니다."
            />
            <div className="mt-3 divide-y divide-zinc-100">
              {cards.map((card) => (
                <CardRow
                  key={card.card_id}
                  card={card}
                  value={spends[card.card_id] ?? 0}
                  onChange={(amount) => setSpend(card.card_id, amount)}
                />
              ))}
            </div>
          </section>

          <section className="rounded-2xl border border-zinc-200 bg-white p-5 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <StepLabel
              index={2}
              title="이번 달 남은 예상 지출"
              hint="어차피 쓸 돈만 넣어 주세요. 억지로 더 쓰는 금액은 계산에 넣지 않습니다."
            />
            <div className="mt-3">
              <NumberField
                id="planned-spend"
                label="이번 달 남은 예상 지출"
                value={plannedSpend}
                onChange={setPlannedSpend}
                placeholder="0"
                size="lg"
              />
            </div>
          </section>

          {mutation.isError ? (
            <p className="rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-xs text-red-700">
              {mutation.error instanceof ApiError
                ? mutation.error.message
                : "계산하지 못했습니다. 잠시 후 다시 시도해 주세요."}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={!canSubmit}
            className="h-12 w-full rounded-xl bg-zinc-900 text-sm font-semibold text-white transition enabled:hover:bg-zinc-800 enabled:active:scale-[0.99] disabled:bg-zinc-200 disabled:text-zinc-400"
          >
            {mutation.isPending ? "계산 중" : "계산하기"}
          </button>

          <p className="px-1 text-[11px] leading-relaxed text-zinc-400">
            입력한 값은 저장하지 않습니다. 계산 결과는 이 화면에서만 쓰입니다.
          </p>
        </form>
      ) : null}
    </main>
  );
}
