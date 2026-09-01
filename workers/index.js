export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // OPTIONS リクエスト（CORSプリフライト）の処理
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, PATCH, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': '*',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // 転送先URLの構築 (https://discord.com + パス + クエリ)
    const targetUrl = new URL(url.pathname + url.search, 'https://discord.com');

    // リクエストヘッダーの複製とHostヘッダーの書き換え
    const headers = new Headers(request.headers);
    headers.set('Host', 'discord.com');

    const init = {
      method: request.method,
      headers: headers,
      redirect: 'follow',
    };

    if (!['GET', 'HEAD'].includes(request.method)) {
      init.body = request.body;
    }

    try {
      const response = await fetch(targetUrl.toString(), init);
      const responseHeaders = new Headers(response.headers);
      responseHeaders.set('Access-Control-Allow-Origin', '*');

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: responseHeaders,
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 502,
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    }
  },
};
