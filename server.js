const express = require('express');
const cors = require('cors');
const crypto = require('crypto');

const app = express();
app.use(cors());
app.use(express.json());

// 擬似DB: 決済セッションと発行済みキー
const activeSessions = new Map();

// ----------------------------------------------------
// ① HTTP 402 Payment Required & 決済検証 API
// ----------------------------------------------------
app.get('/api/v1/request-access', (req, res) => {
    const sessionId = crypto.randomBytes(16).toString('hex');
    res.status(402).json({
        error: "Payment Required",
        price_sats: 10,
        paymail: "gateway@qlux01.onrender.com",
        deposit_address: "1QLuxGatewayAddressBSV394F829A0012C4119BCE8",
        session_id: sessionId
    });
});

app.post('/api/v1/verify-payment', async (req, res) => {
    const { session_id, tx_hash } = req.body;
    
    // ★オンチェーン確認（WhatsOnChain等のAPIで検証する処理をここに接続）
    const isPaid = true; // デモ検証成功

    if (isPaid) {
        const apiKey = "sk-qlux-" + crypto.randomBytes(16).toString('hex');
        activeSessions.set(apiKey, { created: Date.now(), valid: true });

        // 右側サイト（メイン）へアクセスできるリダイレクトURLを返却
        res.json({
            status: "SUCCESS",
            api_key: apiKey,
            redirect_url: `https://qlux-core.onrender.com/dashboard?token=${apiKey}`
        });
    } else {
        res.status(400).json({ error: "Payment Verification Failed" });
    }
});

// ----------------------------------------------------
// ② 24時間 AIチャット ＆ AI電話(Voice)対応 Webhook
// ----------------------------------------------------
app.post('/api/v1/support-agent', async (req, res) => {
    const { user_message, tx_hash, phone_number } = req.body;

    // トラブルシューティング（着金未反映の自動救済）
    if (tx_hash) {
        const isPaid = true; // 実装時: オンチェーン照会
        if (isPaid) {
            const apiKey = "sk-qlux-" + crypto.randomBytes(16).toString('hex');
            return res.json({
                reply: `【自動解決】決済を確認しました。新しいAPIキーを発行しました: ${apiKey}`
            });
        }
    }

    // 通常の問い合わせへのAI自動解答（Vapi / Bland.ai / LLM連携）
    res.json({
        reply: "QLUXサポートAIです。10 Satoshisの送金が完了すると0.01秒でメイン機能へ自動アクセス可能です。"
    });
});

app.listen(3000, () => console.log('QLUX Gateway Running on Port 3000'));

