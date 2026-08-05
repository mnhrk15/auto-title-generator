# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Japanese hairstyle template generator web application that scrapes hairstyle data from HotPepper Beauty and uses Google's Gemini 3.1 Flash Lite AI to generate marketing templates (titles, menus, comments, hashtags) for beauty salons. The application is built with Flask 3.0.2 (ASGI-enabled) and designed for deployment on Render with optimized performance. Features include Beauty Selection featured keyword integration with gender-based filtering, streamlined UI with blue color theme, and real-time keyword updates.

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
Settings live in `pytest.ini` (testpaths, asyncio_mode=strict, and an `integration` marker
that is excluded by default via `addopts`).

```bash
# Run all tests (tests hitting the real Gemini API are excluded automatically)
pytest

# Run the tests that call the real Gemini API (requires GEMINI_API_KEY)
pytest -m integration

# Run specific test file
pytest tests/test_generator.py -v

# Run tests with detailed output and show local variables on failure
pytest -vvs --tb=long
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
- `/app/main.py`: Blueprint with routes and request parsing
- `/app/error_handlers.py`: App-wide error handlers. Every endpoint returns JSON, including
  404 / 405 / unhandled exceptions. The `HTTPException` handler must stay registered alongside
  the `Exception` one — with only the latter, Flask routes 404s there and they become 500s.
- `/run.py`: Development server entry point
- `/asgi.py`: Production ASGI adapter for async support

**Async Processing Pipeline**:
1. **Web Scraping** (`/app/scraping.py`): `HotPepperScraper` class uses aiohttp to asynchronously scrape hairstyle titles from HotPepper Beauty
2. **AI Generation** (`/app/generator.py`): `TemplateGenerator` only initializes the Gemini client
   and sends the request. The surrounding concerns are separate modules, each testable without an
   API key: `/app/prompts.py` (prompt assembly), `/app/schemas.py` (output schema),
   `/app/gemini_response.py` (response interpretation), `/app/template_validation.py` (validation),
   `/app/seasons.py` (season/color normalization and appending).
3. **Request Handling** (`/app/main.py`): Async route `/api/generate` orchestrates the pipeline.
   `parse_generate_request()` is a pure function — it validates the body and normalizes `seasons`.
   It is the **single** owner of season normalization (it used to run three times per request).

**Service Layer** (`/app/services/`):
- `keyword_analysis.py`: Classifies the input keyword as featured / normal / mixed. Pure logic with
  no I/O, so it is testable without a Flask application context.
- `featured_service.py`: Builds the featured-keyword list (gender filter, projection to public
  fields, degraded-mode message). Flask-free.
- `template_service.py`: Coordinates the scraper and the generator. Returns a `GenerationOutcome`
  dataclass — request-level facts (`is_featured`, `featured_info`) live there, not duplicated into
  every template. Only per-card metadata is attached to templates themselves.
- Services never touch `current_app`. Dependencies (e.g. the featured-keyword repository) are passed
  in as arguments; only routes resolve them. The repository contract is documented as a `Protocol`
  in `featured_keywords.py`, imported under `TYPE_CHECKING` so services stay Flask-free.

**Frontend** (`/app/static/js/`):
- Plain ES modules loaded via `<script type="module">`. No bundler, no `package.json`.
- `main.js` is the entry point and only wires up each module's `init()`.
- `api.js` centralizes fetch calls. Errors surface as `ApiError` with a `kind`
  (`timeout` / `network` / `server` / `app`) so callers branch on a field, not on message text.
- Non-2xx responses are parsed before throwing, so the server's error `code` reaches the UI.
- `dom.js` holds selectors for elements that live as long as the page. Dynamically created
  elements are queried by whoever creates them — that is not a violation. A selector string
  appearing in two modules is. A startup assertion logs any `el` entry that came back null,
  because these are bound to `index.html` by string matching only.
- `toast.js` documents the five notification surfaces and when to use each. They are not five
  copies of the same thing; do not merge them.
- Templates repeated in `index.html` live in `templates/_macros.html`. Character limits come from
  `config.CHAR_LIMITS` via `render_template` — never hardcode them in the template or in JS.
- State lives in module scope (`progress.js`, `template-list.js`). There is no global store, and
  nothing is exposed on `window` — inline `onclick` attributes would not be able to see module
  scope, so all handlers are attached with `addEventListener`.

**Configuration Management** (`/app/config.py`):
- Environment-based configuration with dotenv support
- Separate settings for scraping, AI generation, and deployment
- Season/color choices (`SEASON_COLOR_CHOICES`) and the post-processing append rules
- Character limits for each template component

### Data Flow
1. User submits keyword + gender + optional season/color checkboxes (ladies only) via web form (model automatically set to the default Gemini model)
2. `HotPepperScraper.scrape_titles_async()` scrapes relevant hairstyle titles
3. `TemplateGenerator.generate_templates_async()` sends titles + context to the Gemini API
4. Generated templates are validated against character limits and requirements
5. `TemplateGenerator._apply_season_keywords()` appends the selected season/color keywords to short titles (ladies only)
6. Results returned as JSON to frontend

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
- `SCRAPER_VERIFY_SSL`: Scraper certificate verification (default: true, using the certifi CA bundle).
  Set to 'false' only as a last resort in a local environment that cannot verify the chain.
- `LOG_DIR`: Log output directory (defaults to `<project root>/logs`)
- `FEATURED_KEYWORDS_PATH`: Featured keywords JSON path (defaults to `app/data/featured_keywords.json`)

### Google Gemini SDK Configuration

**SDK**: `google-genai 1.70.0`
- Google GenAI SDK for Gemini 3 models
- Used in `TemplateGenerator` constructor: `self.client = genai.Client(api_key=self.settings.gemini_api_key)`
- Optimized generation with `thinkingLevel=MINIMAL` setting (minimizes internal reasoning for speed)
- Structured output via `response_schema` (see `app/schemas.py`) — the model is constrained to the
  JSON schema, so no manual JSON extraction from the response text is needed
- Default model: `gemini-3.1-flash-lite` (no user selection required)
- Supported models: `gemini-3.1-flash-lite`, `gemini-3-flash-preview`
- Located at `app/generator.py`

**Performance Optimization**:
```python
# SDK configuration in generator.py
request_config = types.GenerateContentConfig(
    temperature=config.GEMINI_TEMPERATURE,
    max_output_tokens=config.GEMINI_MAX_OUTPUT_TOKENS,
    thinking_config=types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.MINIMAL  # Minimizes thinking for speed
    ),
    response_mime_type='application/json',
    response_schema=GenerationResult,
    http_options=types.HttpOptions(
        timeout=config.GEMINI_REQUEST_TIMEOUT_MS,
        retry_options=types.HttpRetryOptions(attempts=config.GEMINI_RETRY_ATTEMPTS, ...),
    ),
)
```

**Timeout budget**: `gunicorn.conf.py` has `timeout = 120` and the frontend aborts at 120s.
That ceiling covers the **whole request — scraping plus generation**, not generation alone:
- generation: `40s x 2 attempts + 4s max backoff` ≈ 84s
- scraping: `MAX_PAGES x (10s per page + up to 3s delay)`

With the production `MAX_PAGES=1` this is ≈ 97s and fits. With the default `MAX_PAGES=3` it is
≈ 123s and can exceed the worker timeout, so raising `MAX_PAGES` means revisiting the gunicorn
timeout and the frontend `AbortController` too. Raising attempts to 3 at 45s blows the budget on
generation alone. These values are coupled — change them together.

### Async/Await Usage
The application uses async extensively throughout the entire pipeline:

**Core Async Components**:
- `HotPepperScraper.scrape_titles_async()`: Async web scraping with aiohttp
- `TemplateGenerator.generate_templates_async()`: Async AI generation with Gemini
- Main API endpoint `/api/generate`: Fully async request handling
- `generate_templates_for_request()` (`/app/services/template_service.py`): Orchestrates async
  scraping + generation and returns a `GenerationOutcome`

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
- Season/color keywords are never injected into the prompt; they are appended in Python after generation (`_apply_season_keywords`), and only for ladies
- Prompt vocabulary, title/menu/comment/hashtag examples are branched by gender so that ladies-oriented color words never reach the mens prompt

### Production Deployment Notes

**ASGI Configuration**:
- `asgi.py`: WsgiToAsgi adapter wraps Flask for async compatibility
- `gunicorn.conf.py`: Configured with UvicornWorker for async support
- 2 workers optimized for Render Starter plan resource constraints
- Memory leak prevention with max_requests=1000

**SSL and Security**:
- SSL verification is **on by default in every environment**, using the certifi CA bundle.
  `FLASK_ENV` is not read anywhere — an earlier version gated verification on it, which silently
  disabled verification in production because `FLASK_ENV` was never set on Render.
- Disable it only by setting `SCRAPER_VERIFY_SSL=false` explicitly (local development only).
  Values that cannot be parsed as a boolean fall back to the default rather than to `false`,
  so a typo cannot silently turn verification off.

**Logging and Monitoring**:
- Handlers are attached to the **root logger** in `setup_logging()`, so `app.logger` and every
  module's `logging.getLogger(__name__)` share them. Registration is idempotent across repeated
  `create_app()` calls.
- Two sinks: rotating file logs (1MB limit, 10 backups) in `LOG_DIR/app.log`, **and stderr**.
  The stderr handler is required — Render collects the container's stdout/stderr, and the log
  file does not survive a restart. Do not remove it when touching `setup_logging()`.
- Each gunicorn worker is its own process, so `ロギングシステムが初期化されました` appears once
  per worker (2 lines with the default `workers = 2`), not once per deploy.
- Comprehensive request/response logging for debugging
- Performance metrics logging for generation times

## Lint and Formatting

`pyproject.toml` configures ruff (lint + format). There is no type checker.

```bash
ruff check .          # lint
ruff check . --fix
ruff format .
```

Notes on the configuration:
- `E501` (line length) is deliberately not selected — the formatter does not wrap strings, so
  Japanese f-string log lines would show up as violations that cannot be fixed.
- `quote-style = "preserve"` keeps the existing mix of `'` and `"`.
- `*.md` is excluded: ruff 0.16 formats Python code blocks inside Markdown, and documentation
  snippets are illustrative fragments that need not match the real code.

## Testing Structure

Tests are organized by component:
- `test_prompts.py`: Prompt assembly (pure functions, no API key needed)
- `test_generator.py`: Result extraction, template validation, season keyword appending
- `test_keyword_analysis.py`: Keyword classification (no Flask context needed)
- `test_scraping.py`: Web scraping functionality with aiohttp mocking
- `test_main.py`: Flask routes, error handling, and response-shape snapshots
- `test_featured_keywords.py` / `test_featured_integration.py`: Featured keyword feature
- `test_integration.py`: Calls the real Gemini API — marked `integration`, excluded by default
- `conftest.py`: Shared fixtures. Resets the settings cache per test so `monkeypatch.setenv` works.

All tests use pytest with async support (`@pytest.mark.asyncio` for async functions).

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
- **gemini-3.1-flash-lite**: Default model for template generation (no user selection needed)
- **thinkingLevel=MINIMAL**: Minimizes internal reasoning for optimized speed
- **temperature=1.0**: Required for Gemini 3 models (values below 1.0 cause degraded output)
- **Structured output**: `response_schema` constrains the model to the expected JSON shape

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
1. Verify `thinking_level` parameter compatibility with new models (Gemini 3 uses `ThinkingLevel` enum)
2. Monitor performance metrics (target: <12 seconds for 20 templates)
3. Update version numbers in `requirements.txt` and documentation
4. Test async functionality with the SDK
5. Validate JSON response parsing works with new model outputs
6. Check character limits still work with updated generation patterns
7. Update `DEFAULT_MODEL` and `SUPPORTED_MODELS` in `app/config.py` (these are the single source of
   truth — the frontend no longer sends a model name)

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.