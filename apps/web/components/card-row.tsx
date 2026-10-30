"use client";

import type { Card } from "@pypo/api-client";

import { NumberField } from "./number-field";

export function CardRow({
  card,
  value,
  onChange,
}: {
  card: Card;
  value: number;
  onChange: (value: number) => void;
}) {
  const ladder = card.tiers.map((tier) => `${Math.round(tier.spend_threshold / 10_000)}만`).join(" · ");

  return (
    <div className="flex items-center gap-3 py-3">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-zinc-900">{card.name}</p>
        <p className="mt-0.5 truncate text-[11px] text-zinc-400">
          {card.issuer} · {ladder}원
        </p>
      </div>
      <div className="w-[42%] max-w-40 shrink-0">
        <NumberField
          id={`spend-${card.card_id}`}
          label={`${card.name} 이번 달 실적`}
          value={value}
          onChange={onChange}
          placeholder="0"
        />
      </div>
    </div>
  );
}
