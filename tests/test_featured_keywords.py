"""
FeaturedKeywordsManagerのユニットテスト

特集キーワード機能の以下の機能をテストする:
- JSON読み込み機能
- キーワード判定機能
- エラーハンドリング機能
- データ検証機能
"""

import pytest
import json
import os
import tempfile
import shutil
import copy
from unittest.mock import patch, mock_open, MagicMock
from app.featured_keywords import (
    FeaturedKeywordsManager,
    FeaturedKeywordsError,
    FeaturedKeywordsLoadError,
    FeaturedKeywordsValidationError
)


class TestFeaturedKeywordsManager:
    """FeaturedKeywordsManagerのテストクラス"""
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def valid_keywords_data(self):
        """有効な特集キーワードデータ"""
        return [
            {
                "name": "テスト用くびれヘア",
                "keyword": "くびれヘア",
                "gender": "ladies",
                "condition": "テスト用の掲載条件です。"
            },
            {
                "name": "テスト用韓国風マッシュ",
                "keyword": "韓国風マッシュ",
                "gender": "mens",
                "condition": "テスト用のメンズ掲載条件です。"
            }
        ]
    
    @pytest.fixture
    def valid_keywords_file(self, temp_dir, valid_keywords_data):
        """有効な特集キーワードJSONファイルを作成"""
        file_path = os.path.join(temp_dir, 'valid_keywords.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(valid_keywords_data, f, ensure_ascii=False, indent=2)
        return file_path
    
    @pytest.fixture
    def empty_keywords_file(self, temp_dir):
        """空の特集キーワードJSONファイルを作成"""
        file_path = os.path.join(temp_dir, 'empty_keywords.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump([], f)
        return file_path
    
    @pytest.fixture
    def malformed_json_file(self, temp_dir):
        """不正なJSON形式のファイルを作成"""
        file_path = os.path.join(temp_dir, 'malformed.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('{"invalid": "json", "missing": "closing_bracket"')
        return file_path
    
    @pytest.fixture
    def invalid_structure_file(self, temp_dir):
        """不正な構造のJSONファイルを作成"""
        file_path = os.path.join(temp_dir, 'invalid_structure.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"not": "an_array"}, f)
        return file_path
    
    @pytest.fixture
    def invalid_keywords_file(self, temp_dir):
        """無効なキーワードデータを含むJSONファイルを作成"""
        invalid_data = [
            {
                "name": "有効なキーワード",
                "keyword": "有効キーワード",
                "gender": "ladies",
                "condition": "有効な条件"
            },
            {
                "name": "無効なキーワード1",
                "keyword": "無効キーワード1",
                "gender": "invalid_gender",
                "condition": "無効な性別値"
            },
            {
                "keyword": "名前なし",
                "gender": "mens",
                "condition": "名前フィールドが欠落"
            },
            {
                "name": "",
                "keyword": "空の名前",
                "gender": "ladies",
                "condition": "空の名前フィールド"
            },
            {
                "name": "重複キーワード1",
                "keyword": "重複",
                "gender": "ladies",
                "condition": "重複テスト1"
            },
            {
                "name": "重複キーワード2",
                "keyword": "重複",
                "gender": "mens",
                "condition": "重複テスト2"
            }
        ]
        file_path = os.path.join(temp_dir, 'invalid_keywords.json')
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f, ensure_ascii=False, indent=2)
        return file_path
    
    def test_init_with_valid_file(self, valid_keywords_file):
        """有効なJSONファイルでの初期化テスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        assert manager.is_available() is True
        assert len(manager.keywords) == 2
        assert manager.get_last_error() is None
        
        keywords = manager.load_keywords()
        assert len(keywords) == 2
        assert keywords[0]['name'] == "テスト用くびれヘア"
        assert keywords[1]['name'] == "テスト用韓国風マッシュ"
    
    def test_init_with_nonexistent_file(self, temp_dir):
        """存在しないファイルでの初期化テスト"""
        nonexistent_path = os.path.join(temp_dir, 'nonexistent.json')
        manager = FeaturedKeywordsManager(nonexistent_path)
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
        assert "見つかりません" in str(manager.get_last_error())
    
    def test_init_with_empty_file(self, temp_dir):
        """空のファイルでの初期化テスト"""
        empty_file = os.path.join(temp_dir, 'empty.json')
        open(empty_file, 'w').close()  # 空ファイル作成
        
        manager = FeaturedKeywordsManager(empty_file)
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
        assert "空です" in str(manager.get_last_error())
    
    def test_init_with_large_file(self, temp_dir):
        """大きすぎるファイルでの初期化テスト"""
        large_file = os.path.join(temp_dir, 'large.json')
        with open(large_file, 'w') as f:
            # 1MB以上のファイルを作成
            f.write('{"data": "' + 'x' * (1024 * 1024 + 1) + '"}')
        
        manager = FeaturedKeywordsManager(large_file)
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
        assert "大きすぎます" in str(manager.get_last_error())
    
    def test_init_with_malformed_json(self, malformed_json_file):
        """不正なJSON形式でのテスト"""
        manager = FeaturedKeywordsManager(malformed_json_file)
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
        assert "JSON形式が不正" in str(manager.get_last_error())
    
    def test_init_with_invalid_structure(self, invalid_structure_file):
        """不正な構造のJSONでのテスト"""
        manager = FeaturedKeywordsManager(invalid_structure_file)
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsValidationError)
        assert "配列である必要があります" in str(manager.get_last_error())
    
    def test_init_with_empty_array(self, empty_keywords_file):
        """空の配列でのテスト"""
        manager = FeaturedKeywordsManager(empty_keywords_file)
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert manager.get_last_error() is None  # 空の配列はエラーではない
    
    def test_init_with_invalid_keywords(self, invalid_keywords_file):
        """無効なキーワードデータでのテスト"""
        manager = FeaturedKeywordsManager(invalid_keywords_file)
        
        # 有効なキーワードのみが読み込まれる
        assert manager.is_available() is True
        assert len(manager.keywords) >= 1  # 少なくとも1つの有効なキーワードがある
        # 最初のキーワードが有効なキーワードであることを確認
        valid_keyword_found = any(kw['name'] == "有効なキーワード" for kw in manager.keywords)
        assert valid_keyword_found is True
        assert manager.get_last_error() is None  # 部分的な読み込み成功はエラーではない
    
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=100)
    @patch('builtins.open', side_effect=PermissionError("Permission denied"))
    def test_init_with_permission_error(self, mock_open, mock_getsize, mock_exists):
        """ファイル読み込み権限エラーのテスト"""
        manager = FeaturedKeywordsManager('test.json')
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
        assert "読み込み権限がありません" in str(manager.get_last_error())
    
    @patch('os.path.exists', return_value=True)
    @patch('os.path.getsize', return_value=100)
    @patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte'))
    def test_init_with_unicode_error(self, mock_open, mock_getsize, mock_exists):
        """文字エンコーディングエラーのテスト"""
        manager = FeaturedKeywordsManager('test.json')
        
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
        assert "文字エンコーディングエラー" in str(manager.get_last_error())
    
    def test_load_keywords(self, valid_keywords_file):
        """load_keywordsメソッドのテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        keywords = manager.load_keywords()
        
        assert isinstance(keywords, list)
        assert len(keywords) == 2
        assert keywords[0]['name'] == "テスト用くびれヘア"
        
        # 返されるリストが独立したコピーであることを確認
        keywords[0]['name'] = "変更されたテスト"
        original_keywords = manager.load_keywords()
        assert original_keywords[0]['name'] == "テスト用くびれヘア"
    
    def test_is_featured_keyword_valid_cases(self, valid_keywords_file):
        """is_featured_keywordメソッドの有効なケースのテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # 完全一致
        assert manager.is_featured_keyword("くびれヘア") is True
        assert manager.is_featured_keyword("韓国風マッシュ") is True
        
        # 完全一致（日本語では大文字小文字の概念が異なるため）
        assert manager.is_featured_keyword("くびれヘア") is True
        assert manager.is_featured_keyword("韓国風マッシュ") is True
        
        # 前後の空白を無視
        assert manager.is_featured_keyword("  くびれヘア  ") is True
        assert manager.is_featured_keyword("\t韓国風マッシュ\n") is True
        
        # 存在しないキーワード
        assert manager.is_featured_keyword("存在しないキーワード") is False
        assert manager.is_featured_keyword("レイヤーボブ") is False
    
    def test_is_featured_keyword_invalid_inputs(self, valid_keywords_file):
        """is_featured_keywordメソッドの無効な入力のテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # None入力
        assert manager.is_featured_keyword(None) is False
        
        # 空文字列
        assert manager.is_featured_keyword("") is False
        assert manager.is_featured_keyword("   ") is False
        
        # 非文字列型
        assert manager.is_featured_keyword(123) is False
        assert manager.is_featured_keyword([]) is False
        assert manager.is_featured_keyword({}) is False
    
    def test_is_featured_keyword_no_keywords_loaded(self, temp_dir):
        """キーワードが読み込まれていない場合のis_featured_keywordテスト"""
        nonexistent_path = os.path.join(temp_dir, 'nonexistent.json')
        manager = FeaturedKeywordsManager(nonexistent_path)
        
        assert manager.is_featured_keyword("くびれヘア") is False
        assert manager.is_featured_keyword("任意のキーワード") is False
    
    def test_get_keyword_info_valid_cases(self, valid_keywords_file):
        """get_keyword_infoメソッドの有効なケースのテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # 存在するキーワード
        info = manager.get_keyword_info("くびれヘア")
        assert info is not None
        assert info['name'] == "テスト用くびれヘア"
        assert info['keyword'] == "くびれヘア"
        assert info['gender'] == "ladies"
        assert info['condition'] == "テスト用の掲載条件です。"
        
        # 完全一致での取得
        info = manager.get_keyword_info("くびれヘア")
        assert info is not None
        assert info['name'] == "テスト用くびれヘア"
        
        # 前後の空白を無視
        info = manager.get_keyword_info("  韓国風マッシュ  ")
        assert info is not None
        assert info['name'] == "テスト用韓国風マッシュ"
        assert info['gender'] == "mens"
        
        # 存在しないキーワード
        info = manager.get_keyword_info("存在しないキーワード")
        assert info is None
    
    def test_get_keyword_info_returns_copy(self, valid_keywords_file):
        """get_keyword_infoが独立したコピーを返すことのテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        info1 = manager.get_keyword_info("くびれヘア")
        info2 = manager.get_keyword_info("くびれヘア")
        
        # 異なるオブジェクトであることを確認
        assert info1 is not info2
        
        # 一方を変更しても他方に影響しないことを確認
        info1['name'] = "変更されたテスト"
        assert info2['name'] == "テスト用くびれヘア"
    
    def test_get_keyword_info_invalid_inputs(self, valid_keywords_file):
        """get_keyword_infoメソッドの無効な入力のテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # None入力
        assert manager.get_keyword_info(None) is None
        
        # 空文字列
        assert manager.get_keyword_info("") is None
        assert manager.get_keyword_info("   ") is None
        
        # 非文字列型
        assert manager.get_keyword_info(123) is None
        assert manager.get_keyword_info([]) is None
        assert manager.get_keyword_info({}) is None
    
    def test_get_keyword_info_no_keywords_loaded(self, temp_dir):
        """キーワードが読み込まれていない場合のget_keyword_infoテスト"""
        nonexistent_path = os.path.join(temp_dir, 'nonexistent.json')
        manager = FeaturedKeywordsManager(nonexistent_path)
        
        assert manager.get_keyword_info("くびれヘア") is None
        assert manager.get_keyword_info("任意のキーワード") is None
    
    def test_get_all_keywords(self, valid_keywords_file):
        """get_all_keywordsメソッドのテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        all_keywords = manager.get_all_keywords()
        assert isinstance(all_keywords, list)
        assert len(all_keywords) == 2
        
        # 返されるリストが独立したコピーであることを確認
        all_keywords[0]['name'] = "変更されたテスト"
        original_keywords = manager.get_all_keywords()
        assert original_keywords[0]['name'] == "テスト用くびれヘア"
    
    def test_is_available(self, valid_keywords_file, temp_dir):
        """is_availableメソッドのテスト"""
        # 有効なキーワードが読み込まれている場合
        manager_valid = FeaturedKeywordsManager(valid_keywords_file)
        assert manager_valid.is_available() is True
        
        # キーワードが読み込まれていない場合
        nonexistent_path = os.path.join(temp_dir, 'nonexistent.json')
        manager_invalid = FeaturedKeywordsManager(nonexistent_path)
        assert manager_invalid.is_available() is False
    
    def test_reload_keywords(self, temp_dir, valid_keywords_data):
        """reload_keywordsメソッドのテスト"""
        keywords_file = os.path.join(temp_dir, 'reload_test.json')
        
        # 初期データでファイル作成
        with open(keywords_file, 'w', encoding='utf-8') as f:
            json.dump(valid_keywords_data[:1], f, ensure_ascii=False, indent=2)
        
        manager = FeaturedKeywordsManager(keywords_file)
        assert len(manager.keywords) == 1
        
        # ファイルを更新
        with open(keywords_file, 'w', encoding='utf-8') as f:
            json.dump(valid_keywords_data, f, ensure_ascii=False, indent=2)
        
        # 再読み込み
        result = manager.reload_keywords()
        assert result is True
        assert len(manager.keywords) == 2
        assert manager.get_last_error() is None
    
    def test_reload_keywords_with_error(self, temp_dir):
        """reload_keywordsメソッドのエラーケースのテスト"""
        keywords_file = os.path.join(temp_dir, 'reload_error_test.json')
        
        # 初期は有効なファイル
        with open(keywords_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        manager = FeaturedKeywordsManager(keywords_file)
        assert manager.get_last_error() is None
        
        # ファイルを不正な形式に変更
        with open(keywords_file, 'w', encoding='utf-8') as f:
            f.write('{"invalid": "json"')
        
        # 再読み込み（エラーが発生するはず）
        result = manager.reload_keywords()
        assert result is False
        assert manager.get_last_error() is not None
        assert isinstance(manager.get_last_error(), FeaturedKeywordsLoadError)
    
    def test_get_last_error(self, temp_dir):
        """get_last_errorメソッドのテスト"""
        # エラーがない場合
        valid_file = os.path.join(temp_dir, 'valid.json')
        with open(valid_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        
        manager_valid = FeaturedKeywordsManager(valid_file)
        assert manager_valid.get_last_error() is None
        
        # エラーがある場合
        nonexistent_path = os.path.join(temp_dir, 'nonexistent.json')
        manager_error = FeaturedKeywordsManager(nonexistent_path)
        error = manager_error.get_last_error()
        assert error is not None
        assert isinstance(error, FeaturedKeywordsLoadError)
    
    def test_get_health_status(self, valid_keywords_file, temp_dir):
        """get_health_statusメソッドのテスト"""
        # 正常な状態
        manager_valid = FeaturedKeywordsManager(valid_keywords_file)
        status = manager_valid.get_health_status()
        
        assert isinstance(status, dict)
        assert status['is_available'] is True
        assert status['keywords_count'] == 2
        assert status['file_path'] == valid_keywords_file
        assert status['file_exists'] is True
        assert status['last_error'] is None
        assert status['error_type'] is None
        
        # エラー状態
        nonexistent_path = os.path.join(temp_dir, 'nonexistent.json')
        manager_error = FeaturedKeywordsManager(nonexistent_path)
        status_error = manager_error.get_health_status()
        
        assert status_error['is_available'] is False
        assert status_error['keywords_count'] == 0
        assert status_error['file_path'] == nonexistent_path
        assert status_error['file_exists'] is False
        assert status_error['last_error'] is not None
        assert status_error['error_type'] == 'FeaturedKeywordsLoadError'
    
    def test_validation_edge_cases(self, temp_dir):
        """データ検証のエッジケースのテスト"""
        # 長すぎるフィールドのテスト
        long_data = [
            {
                "name": "x" * 51,  # 50文字制限を超える
                "keyword": "テスト",
                "gender": "ladies",
                "condition": "テスト条件"
            },
            {
                "name": "テスト",
                "keyword": "x" * 51,  # 50文字制限を超える
                "gender": "ladies",
                "condition": "テスト条件"
            },
            {
                "name": "テスト",
                "keyword": "テスト",
                "gender": "ladies",
                "condition": "x" * 501  # 500文字制限を超える
            }
        ]
        
        long_file = os.path.join(temp_dir, 'long_fields.json')
        with open(long_file, 'w', encoding='utf-8') as f:
            json.dump(long_data, f, ensure_ascii=False, indent=2)
        
        manager = FeaturedKeywordsManager(long_file)
        
        # すべてのキーワードが無効なので、読み込まれない
        assert manager.is_available() is False
        assert len(manager.keywords) == 0
    
    def test_exact_matching(self, valid_keywords_file):
        """正確なマッチングのテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # 正確なマッチングのテスト
        assert manager.is_featured_keyword("くびれヘア") is True
        assert manager.is_featured_keyword("韓国風マッシュ") is True
        
        # 異なる文字は一致しない
        assert manager.is_featured_keyword("くびれへあ") is False
        assert manager.is_featured_keyword("クビレヘア") is False
        
        # 正確なマッチングでの情報取得
        info = manager.get_keyword_info("くびれヘア")
        assert info is not None
        assert info['name'] == "テスト用くびれヘア"
        
        # 異なる文字では取得できない
        info = manager.get_keyword_info("くびれへあ")
        assert info is None
    
    def test_whitespace_handling(self, valid_keywords_file):
        """空白文字の処理のテスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # 様々な空白文字の組み合わせでテスト
        test_cases = [
            "  くびれヘア  ",
            "\tくびれヘア\t",
            "\nくびれヘア\n",
            " \t くびれヘア \n ",
        ]
        
        for test_case in test_cases:
            assert manager.is_featured_keyword(test_case) is True
            info = manager.get_keyword_info(test_case)
            assert info is not None
            assert info['name'] == "テスト用くびれヘア"
    
    @patch('app.featured_keywords.logger')
    def test_logging_behavior(self, mock_logger, valid_keywords_file):
        """ログ出力の動作テスト"""
        manager = FeaturedKeywordsManager(valid_keywords_file)
        
        # 正常読み込み時のログ確認
        mock_logger.info.assert_called()
        
        # キーワード判定時のログ確認
        manager.is_featured_keyword("くびれヘア")
        mock_logger.debug.assert_called()
        
        # 存在しないキーワードの判定時のログ確認
        manager.is_featured_keyword("存在しないキーワード")
        mock_logger.debug.assert_called()


class TestFeaturedKeywordsExceptions:
    """特集キーワード例外クラスのテスト"""
    
    def test_featured_keywords_error(self):
        """FeaturedKeywordsError基底クラスのテスト"""
        error = FeaturedKeywordsError("テストエラー")
        assert str(error) == "テストエラー"
        assert isinstance(error, Exception)
    
    def test_featured_keywords_load_error(self):
        """FeaturedKeywordsLoadErrorのテスト"""
        error = FeaturedKeywordsLoadError("読み込みエラー")
        assert str(error) == "読み込みエラー"
        assert isinstance(error, FeaturedKeywordsError)
        assert isinstance(error, Exception)
    
    def test_featured_keywords_validation_error(self):
        """FeaturedKeywordsValidationErrorのテスト"""
        error = FeaturedKeywordsValidationError("検証エラー")
        assert str(error) == "検証エラー"
        assert isinstance(error, FeaturedKeywordsError)
        assert isinstance(error, Exception)


class TestFeaturedKeywordsIntegration:
    """FeaturedKeywordsManagerの統合テスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """テスト用の一時ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def valid_keywords_data(self):
        """有効な特集キーワードデータ"""
        return [
            {
                "name": "テスト用くびれヘア",
                "keyword": "くびれヘア",
                "gender": "ladies",
                "condition": "テスト用の掲載条件です。"
            },
            {
                "name": "テスト用韓国風マッシュ",
                "keyword": "韓国風マッシュ",
                "gender": "mens",
                "condition": "テスト用のメンズ掲載条件です。"
            }
        ]
    
    def test_real_data_file_integration(self):
        """実際のデータファイルとの統合テスト"""
        # 実際のfeatured_keywords.jsonファイルを使用
        real_data_path = 'app/data/featured_keywords.json'
        
        if os.path.exists(real_data_path):
            manager = FeaturedKeywordsManager(real_data_path)
            
            # 基本的な動作確認
            assert manager.is_available() is True
            assert len(manager.keywords) > 0
            
            # 実際のキーワードでテスト
            keywords = manager.get_all_keywords()
            if keywords:
                first_keyword = keywords[0]
                assert manager.is_featured_keyword(first_keyword['keyword']) is True
                
                info = manager.get_keyword_info(first_keyword['keyword'])
                assert info is not None
                assert info['name'] == first_keyword['name']
                assert info['gender'] in ['ladies', 'mens']
                assert len(info['condition']) > 0
    
    def test_concurrent_access(self, temp_dir, valid_keywords_data):
        """並行アクセスのテスト"""
        import threading
        import time
        
        # Create a valid keywords file for concurrent access test
        valid_keywords_file = os.path.join(temp_dir, 'concurrent_test.json')
        with open(valid_keywords_file, 'w', encoding='utf-8') as f:
            json.dump(valid_keywords_data, f, ensure_ascii=False, indent=2)
        
        manager = FeaturedKeywordsManager(valid_keywords_file)
        results = []
        errors = []
        
        def worker():
            try:
                for i in range(10):
                    # 様々な操作を並行実行
                    manager.is_featured_keyword("くびれヘア")
                    manager.get_keyword_info("韓国風マッシュ")
                    manager.get_all_keywords()
                    manager.is_available()
                    time.sleep(0.001)  # 短い待機
                results.append("success")
            except Exception as e:
                errors.append(str(e))
        
        # 複数スレッドで並行実行
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # エラーが発生していないことを確認
        assert len(errors) == 0
        assert len(results) == 5
        assert all(result == "success" for result in results)