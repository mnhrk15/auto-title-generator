"""Gemini の構造化出力（response_schema）用スキーマ。

pydantic モデルをそのまま response_schema に渡すことで、
モデルの出力が JSON スキーマで強制される。これにより、
レスポンステキストから JSON を手動で抽出する処理が不要になる。

フィールドの宣言順がそのまま出力順（propertyOrdering）になる。
trending_keywords を先に宣言しているのは、
「まずトレンドを分析し、その結果を反映したテンプレートを生成する」という
プロンプトの意図をスキーマ側でも担保するため。

pydantic は google-genai の既存依存なので、requirements.txt への追加は不要。
"""

from typing import List

from pydantic import BaseModel


class TrendingKeyword(BaseModel):
    """参照データのトレンド分析結果1件分。"""

    keyword: str
    count: int
    reason: str


class GeneratedTemplate(BaseModel):
    """生成されたテンプレート1件分。"""

    title: str
    menu: str
    comment: str
    hashtag: List[str]


class GenerationResult(BaseModel):
    """テンプレート生成の出力全体。"""

    trending_keywords: List[TrendingKeyword]
    templates: List[GeneratedTemplate]
