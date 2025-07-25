# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese hairstyle template generator web application that scrapes hairstyle data from HotPepper Beauty and uses Google's Gemini 2.5 Flash Lite AI to generate marketing templates (titles, menus, comments, hashtags) for beauty salons. The application is built with Flask 3.0.2 (ASGI-enabled) and designed for deployment on Render with optimized performance.

## Common Development Commands

### Development Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# or .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (required)
cp .env.example .env  # Edit .env with your GEMINI_API_KEY
```

### Running the Application
```bash
# Development server
python run.py

# Production server (using gunicorn)
gunicorn asgi:app -c gunicorn.conf.py
```

### Testing
```bash
# Run all tests
pytest tests/

# Run all tests with async support (recommended)
pytest tests/ --asyncio-mode=auto

# Run specific test file
pytest tests/test_generator.py -v

# Run with coverage report
pytest tests/ --cov=app --cov-report=html

# Run integration tests (requires GEMINI_API_KEY)
pytest tests/test_integration.py -v

# Run tests excluding UI tests (if Selenium not available)
pytest tests/ -k "not test_ui"

# Run tests with detailed output and show local variables on failure
pytest tests/ -vvs --tb=long
```

### Deployment
The application is configured for Render deployment:
- **Procfile**: Defines the web service startup command
- **render.yaml**: Contains service configuration and environment variables
- **gunicorn.conf.py**: Production server configuration with async workers

## Architecture Overview

### Core Components Architecture

**Flask Application Factory Pattern**:
- `/app/__init__.py`: Application factory with `create_app()` function
- `/app/main.py`: Blueprint with routes and error handlers
- `/run.py`: Development server entry point
- `/asgi.py`: Production ASGI adapter for async support

**Async Processing Pipeline**:
1. **Web Scraping** (`/app/scraping.py`): `HotPepperScraper` class uses aiohttp to asynchronously scrape hairstyle titles from HotPepper Beauty
2. **AI Generation** (`/app/generator.py`): `TemplateGenerator` class uses Google Gemini 2.5 Flash Lite with thinking_budget=0 for ultra-fast template generation (8-second response time for 20 templates)
3. **Request Handling** (`/app/main.py`): Async route `/api/generate` orchestrates the pipeline

**Configuration Management** (`/app/config.py`):
- Environment-based configuration with dotenv support
- Separate settings for scraping, AI generation, and deployment
- Season-specific keywords for prompt engineering
- Character limits for each template component

### Data Flow
1. User submits keyword + gender + optional season via web form
2. `HotPepperScraper.scrape_titles_async()` scrapes relevant hairstyle titles
3. `TemplateGenerator.generate_templates_async()` sends titles + context to Gemini API
4. Generated templates are validated against character limits and requirements
5. Results returned as JSON to frontend

### Key Design Patterns
- **Async Context Managers**: Both scraper and session management use `async with`
- **Error Boundary Pattern**: Comprehensive error handling with specific error codes
- **Template Validation**: Character limits and keyword validation for generated content
- **Rate Limiting**: Built-in delays between scraping requests

## Important Technical Considerations

### Environment Variables (Required)
- `GEMINI_API_KEY`: Google Gemini API key (required for AI generation) - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- `FLASK_SECRET_KEY`: Flask session security key (use secure random string in production)
- `FLASK_DEBUG`: Set to 'True' for development, 'False' for production
- `FLASK_HOST`: Default '0.0.0.0' for Render deployment, '127.0.0.1' for local development
- `PORT`: Server port (Render automatically provides this, defaults to 5000 locally)
- `SCRAPING_DELAY_MIN/MAX`: Rate limiting for web scraping (default: 1-3 seconds, increase if getting blocked)
- `MAX_PAGES`: Limit for scraping pages per request (default: 3, production: 1 for faster performance)
- `FLASK_ENV`: Set to 'production' for SSL verification in scraping
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL - default: INFO)

### Google Gemini SDK Configuration

**Dual SDK Architecture**: The application supports both new and legacy Google Gemini SDKs for maximum compatibility:

**New SDK (Primary)**: `google-genai 1.27.0`
- Supports thinking_budget parameter for performance optimization
- Used in `TemplateGenerator` constructor: `self.client = new_genai.Client(api_key=config.GEMINI_API_KEY)`
- Ultra-fast generation with `thinking_budget=0` setting (disables internal reasoning)
- Model: `gemini-2.5-flash-lite` for maximum speed
- Located at `app/generator.py:27`

**Legacy SDK (Fallback)**: `google-generativeai 0.8.5`
- Automatic fallback when new SDK fails (see `app/generator.py:249`)
- Used via: `genai.GenerativeModel('gemini-2.5-flash-lite')`
- Maintains backward compatibility for all deployment environments

**Performance Optimization**:
```python
# New SDK configuration in generator.py
config_with_thinking = types.GenerateContentConfig(
    temperature=0.7,
    max_output_tokens=8192,
    thinking_config=types.ThinkingConfig(
        thinking_budget=0  # Disables thinking process for max speed
    )
)
```

**Performance Metrics**:
- Previous model (gemini-2.0-flash): ~27 seconds
- Current model (gemini-2.5-flash-lite + thinking_budget=0): ~8 seconds
- **Performance improvement: 71% faster**

### Async/Await Usage
The application uses async extensively throughout the entire pipeline:

**Core Async Components**:
- `HotPepperScraper.scrape_titles_async()`: Async web scraping with aiohttp
- `TemplateGenerator.generate_templates_async()`: Async AI generation with Gemini
- Main API endpoint `/api/generate`: Fully async request handling
- `process_template_generation()`: Orchestrates async scraping + generation

**Session Management**:
- Async context managers (`async with`) for HTTP sessions
- Proper session cleanup with `__aenter__`/`__aexit__`
- Backward compatibility with sync context managers

**Error Handling**:
- Async-aware exception handling in all components
- Proper async teardown in test fixtures

### Japanese Text Handling
- All templates and content are in Japanese
- Character counting is critical for social media compliance
- Season-specific Japanese keywords are used for prompt engineering

### Production Deployment Notes

**ASGI Configuration**:
- `asgi.py`: WsgiToAsgi adapter wraps Flask for async compatibility
- `gunicorn.conf.py`: Configured with UvicornWorker for async support
- 2 workers optimized for Render Starter plan resource constraints
- Memory leak prevention with max_requests=1000

**SSL and Security**:
- Development: SSL verification disabled for local testing
- Production: Full SSL verification enabled when FLASK_ENV='production'
- Environment-based SSL context switching in scraper

**Logging and Monitoring**:
- Rotating file logs (1MB limit, 10 backups) in `/logs/app.log`
- Comprehensive request/response logging for debugging
- Performance metrics logging for generation times

## Testing Structure

Tests are organized by component:
- `test_generator.py`: AI template generation testing with async support
- `test_scraping.py`: Web scraping functionality with aiohttp mocking
- `test_main.py`: Flask route and error handling with async endpoints
- `test_integration.py`: End-to-end workflow testing requiring real API key
- `test_ui.py`: Frontend functionality using Selenium (skipped if not available)
- `conftest.py`: Shared test fixtures with automatic environment setup

All tests use pytest with async support (`@pytest.mark.asyncio` for async functions). UI tests are automatically skipped if Selenium dependencies are not available.

## Important Development Guidelines

### From Cursor Rules
- Always verify existing functionality before implementing new features to prevent duplication
- Maintain consistency in naming conventions and directory structure
- UI/UX changes require explicit approval - do not modify layouts, colors, fonts, or spacing without permission
- Do not change specified technology stack versions without approval
- Follow the existing async patterns when adding new functionality

### Code Quality Requirements
- All new async functions must have proper error handling
- Template validation must be maintained for character limits
- Logging should be comprehensive for debugging scraping and AI generation issues
- Japanese text encoding must be handled properly throughout

### Performance Considerations

**AI Generation Optimization**:
- **Gemini 2.5 Flash Lite**: Fastest available model for template generation
- **thinking_budget=0**: Disables internal reasoning for maximum speed
- **Performance metrics**: ~8 seconds for 20 templates (71% improvement over previous)
- **Dual SDK strategy**: New SDK primary with automatic fallback to legacy SDK

**Resource Management**:
- **Memory optimization**: gunicorn max_requests=1000 prevents memory leaks
- **Worker limits**: 2 workers for Render Starter plan resource constraints
- **Connection pooling**: aiohttp session reuse for efficient HTTP connections
- **Rate limiting**: Configurable delays between scraping requests (1-3 seconds)

**Deployment Optimization**:
- **MAX_PAGES=1** in production for faster scraping with minimal resource usage
- **Async everywhere**: Full async pipeline from scraping to generation
- **Context managers**: Proper resource cleanup with async session management

### Model and SDK Management
When updating AI models or SDKs:
1. Test both new and legacy SDK paths in `generator.py:235-258`
2. Verify `thinking_budget` parameter compatibility with new models
3. Monitor performance metrics (target: <10 seconds for 20 templates)
4. Ensure fallback functionality works correctly (`except` block at line 249)
5. Update version numbers in `requirements.txt` and documentation
6. Test async functionality with both SDK paths
7. Validate JSON response parsing works with new model outputs
8. Check character limits still work with updated generation patterns

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.