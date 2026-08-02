import { routing } from "@/src/i18n/routing";
import createMiddleware from "next-intl/middleware";

const intlMiddleware = createMiddleware(routing);

/**
 * When the app sits behind a reverse proxy (Cloudflare Tunnel, nginx,
 * a Vercel preview, …), Next.js dev mode reads the *internal* listening
 * port (3000) and bakes it into redirect URLs. That produces broken
 * Location headers like `https://<tunnel>:3000/foo` which the browser
 * cannot reach because the tunnel listens on 443/80. We post-process the
 * intl middleware's response to:
 *   1. Strip the `:3000` (and any other dev-server port) from Location.
 *   2. Rewrite the host to the X-Forwarded-Host the proxy gave us, so
 *      we don't accidentally redirect to localhost when the proxy is
 *      forwarding a public hostname.
 * In direct localhost dev (no proxy) this is a no-op because
 * X-Forwarded-Host isn't set and we leave the URL alone.
 */
function fixForwardedLocation(req: Request, res: Response): Response {
  const location = res.headers.get("location");
  if (!location) return res;

  const forwardedHost = req.headers.get("x-forwarded-host");
  const forwardedProto = req.headers.get("x-forwarded-proto");
  if (!forwardedHost) return res;

  try {
    // `location` may be relative ("/foo") or absolute. Resolve against
    // the request URL to handle both.
    const url = new URL(location, req.url);
    const original = url.toString();
    url.host = forwardedHost;
    url.protocol = forwardedProto ? `${forwardedProto}:` : url.protocol;
    url.port = ""; // drop the dev-server port — the proxy listens on 443/80
    const rewritten = url.toString();
    if (rewritten === original) return res;
    const newHeaders = new Headers(res.headers);
    newHeaders.set("location", rewritten);
    return new Response(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: newHeaders,
    });
  } catch {
    return res;
  }
}

export default async function middleware(req: Request) {
  const res = await intlMiddleware(req);
  return fixForwardedLocation(req, res);
}

export const config = {
  matcher: ["/((?!api|_next|_vercel|.*\\..*).*)"],
};
