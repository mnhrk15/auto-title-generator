timeout = 120
workers = 2 # Starterプラン(共有CPU)を考慮し2に設定。メモリ使用量を監視し、問題があれば1に戻すことを推奨。
worker_class = 'uvicorn.workers.UvicornWorker' # aiohttp/asyncioベースのアプリのため、非同期ワーカーに変更

# リソースが限られた環境でのメモリリークを防ぎ、安定性を向上させるための設定
max_requests = 1000
max_requests_jitter = 50

# bind = "0.0.0.0:10000" # Renderがportを環境変数で提供するため通常不要
# loglevel = "debug" # デバッグ用にログレベルを上げる場合 