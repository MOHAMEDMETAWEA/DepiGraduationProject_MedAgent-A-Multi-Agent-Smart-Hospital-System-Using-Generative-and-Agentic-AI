import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const nextConfig: NextConfig = {
  // Next.js 16 dev mode rejects HMR / dev-resource requests whose Origin
  // isn't the default localhost binding. When the app sits behind a
  // tunnel (Cloudflare quick tunnel, ngrok, …) the browser sees the
  // tunnel hostname as the origin and Next blocks it with:
  //   "Blocked cross-origin request to Next.js dev resource …"
  // The page HTML renders but the JS bundles never finish wiring up,
  // so the user sees a blank page. We explicitly allow every tunnel
  // host we expose so HMR + RSC can complete. Production builds ignore
  // this setting.
  allowedDevOrigins: [
    "*.trycloudflare.com",
    "*.ngrok-free.app",
    "*.ngrok.io",
    "*.loca.lt",
  ],
};

export default withNextIntl(nextConfig);
