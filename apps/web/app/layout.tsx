import type { Metadata, Viewport } from "next";
import Link from "next/link";

import "./globals.css";

import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "이번 달 카드 배분",
  description: "남은 지출을 어느 카드에 몰아야 다음 달 혜택 구간을 넘는지 계산합니다.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#fafafa",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-dvh font-sans">
        <Providers>{children}</Providers>
        <footer className="mx-auto w-full max-w-2xl px-4 pb-10">
          <div className="flex items-center justify-between border-t border-zinc-200 pt-5 text-[11px] text-zinc-400">
            <span>pypo</span>
            <Link
              href="/privacy"
              className="underline-offset-4 transition hover:text-zinc-600 hover:underline"
            >
              개인정보 처리방침
            </Link>
          </div>
        </footer>
      </body>
    </html>
  );
}
