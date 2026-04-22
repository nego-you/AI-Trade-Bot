-- トレードログとAI推論結果を保存するテーブル
CREATE TABLE IF NOT EXISTS trade_logs (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ticker_symbol VARCHAR(10) NOT NULL,
    strategy_type VARCHAR(20), -- Strategy A or B
    panic_score INT,           -- Ollama/Geminiによるスコア
    ai_decision JSONB,         -- LLMの推論プロセス全文
    execution_status VARCHAR(20), -- BUY, SKIP, ERROR
    market_context JSONB       -- ダウ、VIXなどのマクロ変数
);

-- スクレイピングしたニュースの生データ
CREATE TABLE IF NOT EXISTS news_articles (
    id SERIAL PRIMARY KEY,
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    content TEXT,
    source_url TEXT,
    is_processed BOOLEAN DEFAULT FALSE
);