import { routing } from "@/src/i18n/routing";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, setRequestLocale } from "next-intl/server";
import { AuthHydrator } from "@/components/layout/auth-hydrator";
import { ThemeProvider } from "@/components/layout/theme-provider";
import { notFound } from "next/navigation";
import { LocaleHtmlSync } from "@/components/layout/locale-html-sync";

type Props = {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
};

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: Props) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as (typeof routing.locales)[number])) {
    notFound();
  }

  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
      <ThemeProvider>
        <LocaleHtmlSync locale={locale} />
        <AuthHydrator />
        {children}
      </ThemeProvider>
    </NextIntlClientProvider>
  );
}
