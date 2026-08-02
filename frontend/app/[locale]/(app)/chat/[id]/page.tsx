"use client";

import { useRouter } from "@/src/i18n/navigation";
import { use } from "react";

export default function ChatByIdPage({ params }: { params: Promise<{ id: string; locale: string }> }) {
  const { locale: _locale } = use(params);
  // Redirect to unified chat page — conversation loading handled there
  const router = useRouter();
  router.replace(`/${_locale}/chat`);
  return null;
}
