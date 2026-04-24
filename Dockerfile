# ベースとなるPythonの環境（軽量版）
FROM python:3.11-slim

# コンテナ内での作業ディレクトリ（部屋）を設定
WORKDIR /app

# 必要なパッケージのリスト（requirements.txt）を先にコピー
COPY requirements.txt .

# パッケージを一括インストール
RUN pip install --no-cache-dir -r requirements.txt

# 残りのプログラムファイル（srcフォルダなど）をすべてコピー
COPY . .

# 【変更】コンテナ起動時に main.py を実行する
CMD ["python", "main.py"]