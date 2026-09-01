# Discord API Proxy for Cloudflare Workers

Render などの共有ホスティング環境で発生する Discord API の 429 レート制限 (Cloudflare IP Block) を回避するためのリバースプロキシです。

## デプロイ方法

### 1. Cloudflare ダッシュボードから直接作成する場合 (簡単)
1. [Cloudflare Dashboard](https://dash.cloudflare.com/) にログイン
2. **Compute (Workers) > Workers & Pages** を選択
3. **Create Application** > **Create Worker** をクリック
4. 任意の名前（例: `discord-api-proxy`）をつけて **Deploy**
5. **Edit code** を開き、`index.js` の内容を貼り付けて **Save and deploy**
6. 発行された URL（例: `https://discord-api-proxy.xxxx.workers.dev`）をコピー

### 2. Wrangler CLI でデプロイする場合
```bash
cd workers
npm install -g wrangler
wrangler login
wrangler deploy
```

---

## Bot側の設定

Render または `.env` の環境変数にプロキシURLを設定します。

```env
DISCORD_API_PROXY=https://discord-api-proxy.xxxx.workers.dev
```
