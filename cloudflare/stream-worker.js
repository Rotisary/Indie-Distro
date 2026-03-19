export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204 });
    }

    const cookieName = env.STREAM_COOKIE_NAME || "stream_auth";
    const secret = env.STREAM_COOKIE_SECRET;
    if (!secret) {
      return new Response("Missing stream cookie secret", { status: 500 });
    }

    const cookieHeader = request.headers.get("Cookie") || "";
    const cookieValue = getCookieValue(cookieHeader, cookieName);
    if (!cookieValue) {
      return new Response("Unauthorized", { status: 403 });
    }

    const [payloadB64, signatureB64] = cookieValue.split(".");
    if (!payloadB64 || !signatureB64) {
      return new Response("Unauthorized", { status: 403 });
    }

    const isValid = await verifySignature(payloadB64, signatureB64, secret);
    if (!isValid) {
      return new Response("Unauthorized", { status: 403 });
    }

    let payload;
    try {
      payload = JSON.parse(new TextDecoder().decode(base64urlToBytes(payloadB64)));
    } catch (error) {
      return new Response("Unauthorized", { status: 403 });
    }

    const now = Math.floor(Date.now() / 1000);
    if (!payload.exp || payload.exp < now) {
      return new Response("Unauthorized", { status: 403 });
    }

    const url = new URL(request.url);
    const allowedPath = payload.path || "/";
    if (!url.pathname.startsWith(allowedPath)) {
      return new Response("Unauthorized", { status: 403 });
    }

    return fetch(request);
  },
};

function getCookieValue(cookieHeader, name) {
  const parts = cookieHeader.split(";");
  for (const part of parts) {
    const [key, ...rest] = part.trim().split("=");
    if (key === name) {
      return rest.join("=");
    }
  }
  return "";
}

async function verifySignature(payloadB64, signatureB64, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"]
  );

  return crypto.subtle.verify(
    "HMAC",
    key,
    base64urlToBytes(signatureB64),
    new TextEncoder().encode(payloadB64)
  );
}

function base64urlToBytes(input) {
  const pad = input.length % 4 === 0 ? "" : "=".repeat(4 - (input.length % 4));
  const base64 = (input + pad).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}
