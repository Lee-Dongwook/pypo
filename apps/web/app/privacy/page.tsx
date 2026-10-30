import fs from "node:fs";
import path from "node:path";

import type { Metadata } from "next";
import Link from "next/link";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

export const metadata: Metadata = {
  title: "개인정보 처리방침",
  description: "카드 실적 배분 계산기의 개인정보 처리방침입니다.",
};

/**
 * 처리방침 원문은 `docs/PRIVACY_POLICY.md` 한 곳에만 둔다.
 * 빌드 시점에 읽어 정적 페이지로 굽기 때문에, 문구를 고치면 재배포해야 반영된다.
 */
function readPolicy(): string {
  const candidates = [
    path.resolve(process.cwd(), "../../docs/PRIVACY_POLICY.md"),
    path.resolve(process.cwd(), "docs/PRIVACY_POLICY.md"),
  ];
  const file = candidates.find((candidate) => fs.existsSync(candidate));
  if (!file) {
    throw new Error(`개인정보 처리방침 원문을 찾지 못했습니다: ${candidates.join(", ")}`);
  }
  return fs.readFileSync(file, "utf8");
}

export default function PrivacyPage() {
  const markdown = readPolicy();
  const body = markdown.replace(/^#\s+.*\r?\n+/, "");
  const hasPlaceholder = body.includes("{{");

  return (
    <main className="mx-auto w-full max-w-2xl px-4 pb-16 pt-10">
      <Link
        href="/"
        className="text-xs font-medium text-zinc-400 underline-offset-4 transition hover:text-zinc-600 hover:underline"
      >
        ← 계산기로
      </Link>

      <h1 className="mt-4 text-2xl font-semibold tracking-tight text-zinc-900">개인정보 처리방침</h1>

      {hasPlaceholder ? (
        <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[11px] leading-relaxed text-amber-900">
          이 문서는 아직 초안입니다. 운영자 정보와 보유 기간이 채워지지 않았습니다. 공개 전에{" "}
          <code className="font-mono">docs/PRIVACY_POLICY.md</code>의 자리표시자를 채워 주세요.
        </p>
      ) : null}

      <article className="prose prose-zinc prose-sm mt-8 max-w-none prose-headings:font-semibold prose-headings:tracking-tight prose-h2:mt-10 prose-h2:text-base prose-h2:text-zinc-900 prose-p:leading-relaxed prose-li:leading-relaxed prose-strong:text-zinc-900 prose-a:text-zinc-900 prose-a:underline prose-a:underline-offset-2 prose-th:border prose-th:border-zinc-200 prose-th:bg-zinc-50 prose-th:px-3 prose-th:py-2 prose-td:border prose-td:border-zinc-200 prose-td:px-3 prose-td:py-2">
        <Markdown remarkPlugins={[remarkGfm]}>{body}</Markdown>
      </article>
    </main>
  );
}
