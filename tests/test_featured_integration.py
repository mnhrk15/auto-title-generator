"""
API拡張機能の統合テスト

特集キーワード機能のAPI統合テストを実装する:
- 特集キーワードAPI (/api/featured-keywords) のテスト
- テンプレート生成API (/api/generate) の特集対応テスト
- エンドツーエンドの動作検証テスト

モックが返すテンプレートには **メタデータを含めない**。
メタデータは template_service._attach_metadata が付けるものであり、
モック側で先回りして埋めると、その関数を削除してもテストが通ってしまう。
"""

import json

FEATURED_LADIES = {
    'name': 'テスト用くびれヘア',
    'keyword': 'くびれヘア',
    'gender': 'ladies',
    'condition': 'スタイル名に『くびれヘア』を含めること。',
}

# 生成器が返す素のテンプレート（メタデータなし）
RAW_TEMPLATES = [
    {
        'title': '大人可愛いくびれヘアスタイル',
        'menu': 'カット + カラー',
        'comment': '柔らかい質感に仕上げました。',
        'hashtag': ['#くびれヘア', '#大人可愛い'],
    },
    {
        'title': 'トレンドのくびれヘアでイメチェン',
        'menu': 'カット + パーマ',
        'comment': '動きのあるシルエットです。',
        'hashtag': ['#くびれヘア', '#トレンド'],
    },
]


class TestFeaturedKeywordsAPI:
    """特集キーワードAPI (/api/featured-keywords) のテストクラス"""

    def test_get_featured_keywords_success(self, use_repository, client):
        """特集キーワード取得API - 正常ケース"""
        use_repository([FEATURED_LADIES])

        response = client.get('/api/featured-keywords')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert len(data['keywords']) == 1
        assert data['keywords'][0]['name'] == 'テスト用くびれヘア'
        assert data['keywords'][0]['keyword'] == 'くびれヘア'
        assert data['keywords'][0]['gender'] == 'ladies'
        # 正常時も message キーは常に存在する（値は None）
        assert data['message'] is None

    def test_get_featured_keywords_unavailable(self, use_repository, client):
        """特集キーワード取得API - 機能利用不可ケース"""
        use_repository([], available=False)

        response = client.get('/api/featured-keywords')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['keywords'] == []
        assert '特集キーワードが設定されていません' in data['message']

    def test_get_featured_keywords_with_error(self, use_repository, client):
        """特集キーワード取得API - 読み込みエラーは降格メッセージで返す"""
        from app.errors import FeaturedKeywordsLoadError

        use_repository(
            [],
            available=False,
            last_error=FeaturedKeywordsLoadError('ファイル読み込みエラー'),
        )

        response = client.get('/api/featured-keywords')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['keywords'] == []
        assert '特集キーワードファイルの読み込みに問題があります' in data['message']

    def test_get_featured_keywords_exception_returns_error(self, use_repository, client):
        """特集キーワード取得API - 例外発生時はエラーとして返す

        以前は success: True と error オブジェクトを同時に返していたため、
        success だけを見るフロントエンドでは失敗が成功として扱われていた。
        """
        use_repository([], raises=Exception('予期しないエラー'))

        response = client.get('/api/featured-keywords')

        assert response.status_code == 503
        data = json.loads(response.data)

        assert data['success'] is False
        assert data['error']['code'] == 'FEATURED_KEYWORDS_ERROR'

    def test_get_featured_keywords_data_sanitization(self, use_repository, client):
        """特集キーワード取得API - 欠損フィールドを持つ項目は除外される"""
        use_repository(
            [
                {
                    'name': '有効なキーワード',
                    'keyword': '有効キーワード',
                    'gender': 'ladies',
                    'condition': '有効な条件',
                },
                {
                    'name': '',  # 空の名前
                    'keyword': '無効キーワード',
                    'gender': 'ladies',
                    'condition': '条件',
                },
                {
                    'name': '部分的に有効',
                    'keyword': '部分キーワード',
                    'gender': '',  # 空の性別
                    'condition': '条件',
                },
            ]
        )

        response = client.get('/api/featured-keywords')

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert len(data['keywords']) == 1
        assert data['keywords'][0]['name'] == '有効なキーワード'

    def test_get_featured_keywords_filters_by_gender(self, use_repository, client):
        """性別クエリで絞り込まれる"""
        use_repository(
            [
                FEATURED_LADIES,
                {
                    'name': 'メンズ特集',
                    'keyword': '韓国風マッシュ',
                    'gender': 'mens',
                    'condition': '条件',
                },
            ]
        )

        response = client.get('/api/featured-keywords?gender=mens')

        data = json.loads(response.data)
        assert [k['gender'] for k in data['keywords']] == ['mens']


class TestTemplateGenerationAPI:
    """テンプレート生成API (/api/generate) の特集対応テストクラス"""

    def test_generate_with_featured_keyword(self, use_repository, client, fake_pipeline):
        """テンプレート生成API - 特集キーワードでの生成テスト

        メタデータはモックではなく template_service が付けることを確認する。
        """
        use_repository([FEATURED_LADIES])

        with fake_pipeline(templates=[dict(t) for t in RAW_TEMPLATES]):
            response = client.post(
                '/api/generate',
                json={'keyword': 'くびれヘア', 'gender': 'ladies', 'seasons': []},
            )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['is_featured'] is True

        assert data['featured_keyword_info']['name'] == 'テスト用くびれヘア'
        assert (
            data['featured_keyword_info']['condition'] == 'スタイル名に『くびれヘア』を含めること。'
        )

        assert len(data['templates']) == 2
        for template in data['templates']:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'

    def test_generate_with_normal_keyword(self, use_repository, client, fake_pipeline):
        """テンプレート生成API - 通常キーワードでの生成テスト"""
        use_repository([FEATURED_LADIES])

        with fake_pipeline(templates=[dict(t) for t in RAW_TEMPLATES]):
            response = client.post(
                '/api/generate',
                json={'keyword': 'ボブ', 'gender': 'ladies', 'seasons': []},
            )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['is_featured'] is False
        assert data['featured_keyword_info'] is None

        assert len(data['templates']) == 2
        for template in data['templates']:
            assert template['is_featured'] is False
            assert 'featured_keyword_name' not in template

    def test_generate_with_mixed_keywords(self, use_repository, client, fake_pipeline):
        """テンプレート生成API - 混在キーワードでの生成テスト"""
        use_repository([FEATURED_LADIES])

        with fake_pipeline(templates=[dict(t) for t in RAW_TEMPLATES]):
            response = client.post(
                '/api/generate',
                json={'keyword': 'くびれヘア ボブ', 'gender': 'ladies', 'seasons': []},
            )

        assert response.status_code == 200
        data = json.loads(response.data)

        assert data['success'] is True
        assert data['is_featured'] is True
        assert data['featured_keyword_info']['name'] == 'テスト用くびれヘア'

        assert len(data['templates']) == 2
        for template in data['templates']:
            assert template['is_featured'] is True
            assert template['featured_keyword_name'] == 'テスト用くびれヘア'

    def test_generate_invalid_request(self, client):
        """テンプレート生成API - 無効なリクエストのテスト"""
        response = client.post('/api/generate', json={'keyword': '', 'gender': 'ladies'})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

        response = client.post(
            '/api/generate', json={'keyword': 'テストキーワード', 'gender': 'invalid'}
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert '無効な性別' in data['error']['message']

    def test_generate_invalid_json(self, client):
        """テンプレート生成API - 無効なJSONのテスト"""
        response = client.post(
            '/api/generate', data='invalid json', content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_JSON'

    def test_generate_no_results_found(self, client, fake_scraper):
        """テンプレート生成API - 結果が見つからない場合のテスト"""
        with fake_scraper(titles=[]):
            response = client.post(
                '/api/generate', json={'keyword': '存在しないキーワード', 'gender': 'ladies'}
            )

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error']['code'] == 'NO_RESULTS_FOUND'


class TestEndToEndIntegration:
    """エンドツーエンドの動作検証テストクラス"""

    def test_featured_keywords_to_template_generation_flow(
        self, use_repository, client, fake_pipeline
    ):
        """特集キーワード取得からテンプレート生成までの完全フロー"""
        use_repository([FEATURED_LADIES])

        # Step 1: 特集キーワード一覧を取得
        keywords_response = client.get('/api/featured-keywords')
        assert keywords_response.status_code == 200
        keywords_data = json.loads(keywords_response.data)
        assert keywords_data['success'] is True
        assert len(keywords_data['keywords']) == 1

        featured_keyword = keywords_data['keywords'][0]['keyword']
        assert featured_keyword == 'くびれヘア'

        # Step 2: 取得した特集キーワードでテンプレート生成
        with fake_pipeline(templates=[dict(RAW_TEMPLATES[0])]):
            generate_response = client.post(
                '/api/generate', json={'keyword': featured_keyword, 'gender': 'ladies'}
            )

        assert generate_response.status_code == 200
        generate_data = json.loads(generate_response.data)
        assert generate_data['success'] is True
        assert generate_data['is_featured'] is True
        assert len(generate_data['templates']) >= 1
        assert any('くびれヘア' in t.get('title', '') for t in generate_data['templates'])

    def test_fallback_behavior_when_featured_unavailable(
        self, use_repository, client, fake_pipeline
    ):
        """特集キーワード機能が利用できない場合のフォールバック動作テスト"""
        use_repository([], available=False)

        with fake_pipeline(templates=[dict(RAW_TEMPLATES[0])]):
            response = client.post('/api/generate', json={'keyword': 'ボブ', 'gender': 'ladies'})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['is_featured'] is False
        assert data['featured_keyword_info'] is None
        assert len(data['templates']) >= 1

    def test_error_recovery_and_logging(self, use_repository, client, fake_pipeline):
        """特集キーワード機能が壊れていても生成は続行される

        keyword_analysis はリポジトリの障害を通常キーワード扱いに丸めるため、
        生成全体が落ちることはない。
        """
        use_repository([], raises=Exception('特集キーワード機能エラー'))

        with fake_pipeline(templates=[dict(RAW_TEMPLATES[0])]):
            response = client.post(
                '/api/generate', json={'keyword': 'テストキーワード', 'gender': 'ladies'}
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['is_featured'] is False
        assert len(data['templates']) >= 1
