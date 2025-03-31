import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
import platform
import os
from app import app

# テスト環境でUI実行するかどうかのフラグ
# 環境変数 RUN_UI_TESTS=1 の場合のみUIテストを実行
SKIP_UI_TESTS = os.environ.get('RUN_UI_TESTS') != '1'
skip_reason = "UIテストはRUN_UI_TESTS=1の場合のみ実行されます。"

@pytest.fixture
def app_instance():
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app_instance):
    return app_instance.test_client()

@pytest.fixture
def chrome_driver():
    if SKIP_UI_TESTS:
        pytest.skip(skip_reason)
        
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Apple Silicon用の設定
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        options.binary_location = "/Applications/Chromium.app/Contents/MacOS/Chromium"
        service = ChromeService(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    else:
        service = ChromeService(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=options)
    yield driver
    driver.quit()

@pytest.fixture
def flask_server(app_instance):
    """Flaskサーバーを起動するフィクスチャ"""
    with app_instance.test_client() as client:
        yield client

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_page_title(chrome_driver, flask_server):
    """ページタイトルのテスト"""
    chrome_driver.get('http://localhost:5000')
    assert "ヘアスタイルタイトルジェネレーター" in chrome_driver.title

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_form_elements(chrome_driver, flask_server):
    """フォーム要素の存在確認テスト"""
    chrome_driver.get('http://localhost:5000')
    assert chrome_driver.find_element(By.ID, 'keyword').is_displayed()
    assert chrome_driver.find_element(By.NAME, 'gender').is_displayed()
    assert chrome_driver.find_element(By.ID, 'generate-btn').is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_loading_indicator(chrome_driver, flask_server):
    """ローディングインジケータのテスト"""
    chrome_driver.get('http://localhost:5000')
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # ローディングインジケータが表示されることを確認
    loading = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.ID, 'loading'))
    )
    assert loading.is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_template_display(chrome_driver, flask_server):
    """テンプレート表示のテスト"""
    chrome_driver.get('http://localhost:5000')
    keyword_input = chrome_driver.find_element(By.ID, 'keyword')
    keyword_input.send_keys('ナチュラル')
    
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # テンプレートが表示されることを確認
    template = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'template-card'))
    )
    assert template.is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_keyword_input_validation(chrome_driver, flask_server):
    """キーワード入力のバリデーションテスト"""
    chrome_driver.get('http://localhost:5000')
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # エラーメッセージが表示されることを確認
    error = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'error-message'))
    )
    assert error.is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_template_generation_success(chrome_driver, flask_server):
    """テンプレート生成成功のテスト"""
    chrome_driver.get('http://localhost:5000')
    keyword_input = chrome_driver.find_element(By.ID, 'keyword')
    keyword_input.send_keys('ショート')
    
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # 成功メッセージが表示されることを確認
    success = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'success-message'))
    )
    assert success.is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_error_display(chrome_driver, flask_server):
    """エラー表示のテスト"""
    chrome_driver.get('http://localhost:5000')
    keyword_input = chrome_driver.find_element(By.ID, 'keyword')
    keyword_input.send_keys('!@#$%')  # 無効な入力
    
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # エラーメッセージが表示されることを確認
    error = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'error-message'))
    )
    assert error.is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_responsive_design(chrome_driver, flask_server):
    """レスポンシブデザインのテスト"""
    chrome_driver.get('http://localhost:5000')
    
    # モバイルサイズに設定
    chrome_driver.set_window_size(375, 812)  # iPhone X サイズ
    
    # 要素が表示されていることを確認
    assert chrome_driver.find_element(By.ID, 'keyword').is_displayed()
    assert chrome_driver.find_element(By.ID, 'generate-btn').is_displayed()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_multiple_templates_display(chrome_driver, flask_server):
    """複数テンプレート表示のテスト"""
    chrome_driver.get('http://localhost:5000')
    keyword_input = chrome_driver.find_element(By.ID, 'keyword')
    keyword_input.send_keys('ミディアム')
    
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # 複数のテンプレートが表示されることを確認
    templates = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, 'template-card'))
    )
    assert len(templates) > 1

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_export_csv(chrome_driver, flask_server):
    """CSVエクスポートのテスト"""
    chrome_driver.get('http://localhost:5000')
    export_btn = chrome_driver.find_element(By.ID, 'export-csv')
    assert export_btn.is_enabled()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_export_txt(chrome_driver, flask_server):
    """テキストエクスポートのテスト"""
    chrome_driver.get('http://localhost:5000')
    export_btn = chrome_driver.find_element(By.ID, 'export-txt')
    assert export_btn.is_enabled()

@pytest.mark.skipif(SKIP_UI_TESTS, reason=skip_reason)
def test_copy_functionality(chrome_driver, flask_server):
    """コピー機能のテスト"""
    chrome_driver.get('http://localhost:5000')
    keyword_input = chrome_driver.find_element(By.ID, 'keyword')
    keyword_input.send_keys('ボブ')
    
    generate_btn = chrome_driver.find_element(By.ID, 'generate-btn')
    generate_btn.click()
    
    # コピーボタンが表示されることを確認
    copy_btn = WebDriverWait(chrome_driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'copy-btn'))
    )
    assert copy_btn.is_displayed() 