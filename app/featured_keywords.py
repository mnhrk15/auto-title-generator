"""
Featured Keywords Manager

Beauty Selection特集キーワードの管理を行うモジュール。
JSONファイルからの読み込み、キーワード判定、エラーハンドリングを提供する。
"""

import json
import logging
import os
import traceback
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class FeaturedKeywordsError(Exception):
    """特集キーワード機能に関連するエラーの基底クラス"""
    pass


class FeaturedKeywordsLoadError(FeaturedKeywordsError):
    """特集キーワードの読み込みに関するエラー"""
    pass


class FeaturedKeywordsValidationError(FeaturedKeywordsError):
    """特集キーワードデータの検証に関するエラー"""
    pass


class FeaturedKeywordsManager:
    """特集キーワードの管理クラス
    
    JSONファイルから特集キーワードを読み込み、キーワード判定や
    詳細情報の取得機能を提供する。
    """
    
    def __init__(self, json_path: str = 'app/data/featured_keywords.json'):
        """FeaturedKeywordsManagerの初期化
        
        Args:
            json_path (str): 特集キーワードJSONファイルのパス
        """
        self.json_path = json_path
        self.keywords = []
        self._last_error = None
        self._load_keywords()
    
    def _load_keywords(self) -> None:
        """JSONファイルから特集キーワードを読み込む
        
        エラーが発生した場合は空のリストを設定し、
        特集キーワード機能を無効化する。
        """
        try:
            logger.info(f"特集キーワードファイルの読み込みを開始: {self.json_path}")
            
            if not os.path.exists(self.json_path):
                error_msg = f"特集キーワードファイルが見つかりません: {self.json_path}"
                logger.warning(error_msg)
                self.keywords = []
                self._last_error = FeaturedKeywordsLoadError(error_msg)
                return
            
            # ファイルサイズチェック
            file_size = os.path.getsize(self.json_path)
            if file_size == 0:
                error_msg = f"特集キーワードファイルが空です: {self.json_path}"
                logger.warning(error_msg)
                self.keywords = []
                self._last_error = FeaturedKeywordsLoadError(error_msg)
                return
            
            if file_size > 1024 * 1024:  # 1MB制限
                error_msg = f"特集キーワードファイルが大きすぎます: {file_size} bytes"
                logger.warning(error_msg)
                self.keywords = []
                self._last_error = FeaturedKeywordsLoadError(error_msg)
                return
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"JSONファイル読み込み完了: {type(data)}, 要素数: {len(data) if isinstance(data, list) else 'N/A'}")
            
            # データの検証
            if not isinstance(data, list):
                error_msg = "特集キーワードファイルの形式が不正です: ルート要素は配列である必要があります"
                logger.error(error_msg)
                self.keywords = []
                self._last_error = FeaturedKeywordsValidationError(error_msg)
                return
            
            if len(data) == 0:
                logger.warning("特集キーワードファイルに有効なデータがありません")
                self.keywords = []
                self._last_error = None  # 空のファイルはエラーではない
                return
            
            # 各キーワードの必須フィールドを検証
            validated_keywords = []
            validation_errors = []
            
            for i, item in enumerate(data):
                try:
                    if not isinstance(item, dict):
                        error_msg = f"特集キーワード[{i}]: 辞書形式ではありません"
                        logger.warning(f"{error_msg} - スキップします")
                        validation_errors.append(error_msg)
                        continue
                    
                    required_fields = ['name', 'keyword', 'gender', 'condition']
                    missing_fields = [field for field in required_fields if field not in item or not item[field]]
                    
                    if missing_fields:
                        error_msg = f"特集キーワード[{i}]: 必須フィールドが不足または空です: {missing_fields}"
                        logger.warning(f"{error_msg} - スキップします")
                        validation_errors.append(error_msg)
                        continue
                    
                    # 性別の値を検証
                    if item['gender'] not in ['ladies', 'mens']:
                        error_msg = f"特集キーワード[{i}]: 不正な性別値 '{item['gender']}'"
                        logger.warning(f"{error_msg} - スキップします")
                        validation_errors.append(error_msg)
                        continue
                    
                    # 文字列フィールドの長さ制限チェック
                    if len(item['name']) > 50:
                        error_msg = f"特集キーワード[{i}]: 名前が長すぎます ({len(item['name'])} > 50文字)"
                        logger.warning(f"{error_msg} - スキップします")
                        validation_errors.append(error_msg)
                        continue
                    
                    if len(item['keyword']) > 50:
                        error_msg = f"特集キーワード[{i}]: キーワードが長すぎます ({len(item['keyword'])} > 50文字)"
                        logger.warning(f"{error_msg} - スキップします")
                        validation_errors.append(error_msg)
                        continue
                    
                    if len(item['condition']) > 500:
                        error_msg = f"特集キーワード[{i}]: 条件文が長すぎます ({len(item['condition'])} > 500文字)"
                        logger.warning(f"{error_msg} - スキップします")
                        validation_errors.append(error_msg)
                        continue
                    
                    # 重複チェック
                    duplicate_found = False
                    for existing in validated_keywords:
                        if existing['keyword'].lower().strip() == item['keyword'].lower().strip():
                            error_msg = f"特集キーワード[{i}]: 重複するキーワード '{item['keyword']}'"
                            logger.warning(f"{error_msg} - スキップします")
                            validation_errors.append(error_msg)
                            duplicate_found = True
                            break
                    
                    if duplicate_found:
                        continue
                    
                    validated_keywords.append(item)
                    logger.debug(f"特集キーワード[{i}]を検証完了: {item['name']}")
                    
                except Exception as e:
                    error_msg = f"特集キーワード[{i}]の検証中にエラー: {str(e)}"
                    logger.error(f"{error_msg} - スキップします")
                    validation_errors.append(error_msg)
                    continue
            
            self.keywords = validated_keywords
            self._last_error = None
            
            if validation_errors:
                logger.warning(f"特集キーワード読み込み完了（警告あり）: 有効 {len(validated_keywords)}件, エラー {len(validation_errors)}件")
                for error in validation_errors[:5]:  # 最初の5件のエラーのみログ出力
                    logger.warning(f"  - {error}")
                if len(validation_errors) > 5:
                    logger.warning(f"  - ... 他 {len(validation_errors) - 5} 件のエラー")
            else:
                logger.info(f"特集キーワードを正常に読み込みました: {len(validated_keywords)}件")
            
        except json.JSONDecodeError as e:
            error_msg = f"特集キーワードファイルのJSON形式が不正です: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"JSONDecodeError詳細: {traceback.format_exc()}")
            self.keywords = []
            self._last_error = FeaturedKeywordsLoadError(error_msg)
        except PermissionError as e:
            error_msg = f"特集キーワードファイルの読み込み権限がありません: {str(e)}"
            logger.error(error_msg)
            self.keywords = []
            self._last_error = FeaturedKeywordsLoadError(error_msg)
        except UnicodeDecodeError as e:
            error_msg = f"特集キーワードファイルの文字エンコーディングエラー: {str(e)}"
            logger.error(error_msg)
            self.keywords = []
            self._last_error = FeaturedKeywordsLoadError(error_msg)
        except Exception as e:
            error_msg = f"特集キーワード読み込み中に予期しないエラー: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"予期しないエラー詳細: {traceback.format_exc()}")
            self.keywords = []
            self._last_error = FeaturedKeywordsLoadError(error_msg)
    
    def load_keywords(self) -> List[Dict]:
        """特集キーワードリストを取得する
        
        Returns:
            List[Dict]: 特集キーワードのリスト
        """
        import copy
        return copy.deepcopy(self.keywords)
    
    def is_featured_keyword(self, keyword: str) -> bool:
        """指定されたキーワードが特集キーワードかを判定する
        
        Args:
            keyword (str): 判定対象のキーワード
            
        Returns:
            bool: 特集キーワードの場合True、そうでなければFalse
        """
        if not keyword or not isinstance(keyword, str):
            logger.debug(f"無効なキーワード入力: {keyword} (型: {type(keyword)})")
            return False
        
        if not self.keywords:
            logger.debug("特集キーワードが読み込まれていません")
            return False
        
        try:
            keyword_lower = keyword.lower().strip()
            if not keyword_lower:
                logger.debug("空のキーワードです")
                return False
                
            for item in self.keywords:
                if item['keyword'].lower().strip() == keyword_lower:
                    logger.debug(f"特集キーワードマッチ: '{keyword}' -> '{item['name']}'")
                    return True
            
            logger.debug(f"特集キーワードに該当しません: '{keyword}'")
            return False
        except Exception as e:
            logger.error(f"特集キーワード判定中にエラー: {str(e)}")
            logger.debug(f"特集キーワード判定エラー詳細: {traceback.format_exc()}")
            return False
    
    def get_keyword_info(self, keyword: str) -> Optional[Dict]:
        """特集キーワードの詳細情報を取得する
        
        Args:
            keyword (str): 取得対象のキーワード
            
        Returns:
            Optional[Dict]: 特集キーワードの詳細情報。見つからない場合はNone
        """
        if not keyword or not isinstance(keyword, str):
            logger.debug(f"無効なキーワード入力: {keyword} (型: {type(keyword)})")
            return None
        
        if not self.keywords:
            logger.debug("特集キーワードが読み込まれていません")
            return None
        
        try:
            keyword_lower = keyword.lower().strip()
            if not keyword_lower:
                logger.debug("空のキーワードです")
                return None
                
            for item in self.keywords:
                if item['keyword'].lower().strip() == keyword_lower:
                    logger.debug(f"特集キーワード情報取得成功: '{keyword}' -> '{item['name']}'")
                    import copy
                    return copy.deepcopy(item)
            
            logger.debug(f"特集キーワード情報が見つかりません: '{keyword}'")
            return None
        except Exception as e:
            logger.error(f"特集キーワード情報取得中にエラー: {str(e)}")
            logger.debug(f"特集キーワード情報取得エラー詳細: {traceback.format_exc()}")
            return None
    
    def get_all_keywords(self) -> List[Dict]:
        """すべての特集キーワード情報を取得する
        
        Returns:
            List[Dict]: すべての特集キーワードのリスト
        """
        import copy
        return copy.deepcopy(self.keywords)
    
    def is_available(self) -> bool:
        """特集キーワード機能が利用可能かを確認する
        
        Returns:
            bool: 利用可能な場合True、そうでなければFalse
        """
        return len(self.keywords) > 0
    
    def reload_keywords(self) -> bool:
        """特集キーワードを再読み込みする
        
        Returns:
            bool: 再読み込みが成功した場合True、そうでなければFalse
        """
        try:
            old_count = len(self.keywords)
            old_error = self._last_error
            
            logger.info("特集キーワードの再読み込みを開始します")
            self._load_keywords()
            
            new_count = len(self.keywords)
            
            if self._last_error is None:
                logger.info(f"特集キーワードを正常に再読み込みしました: {old_count}件 -> {new_count}件")
                return True
            else:
                logger.warning(f"特集キーワード再読み込み中にエラーが発生しました: {self._last_error}")
                return False
                
        except Exception as e:
            logger.error(f"特集キーワード再読み込み中に予期しないエラー: {str(e)}")
            logger.debug(f"再読み込みエラー詳細: {traceback.format_exc()}")
            return False
    
    def get_last_error(self) -> Optional[Exception]:
        """最後に発生したエラーを取得する
        
        Returns:
            Optional[Exception]: 最後に発生したエラー。エラーがない場合はNone
        """
        return self._last_error
    
    def get_health_status(self) -> Dict[str, any]:
        """特集キーワード機能の健全性状態を取得する
        
        Returns:
            Dict[str, any]: 健全性状態の情報
        """
        return {
            'is_available': self.is_available(),
            'keywords_count': len(self.keywords),
            'file_path': self.json_path,
            'file_exists': os.path.exists(self.json_path),
            'last_error': str(self._last_error) if self._last_error else None,
            'error_type': type(self._last_error).__name__ if self._last_error else None
        }