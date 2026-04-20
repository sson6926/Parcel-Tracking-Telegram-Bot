# Architecture Documentation

## Overview

This is a Telegram bot for tracking shipments from multiple carriers (JT Express, Shopee Express). The project follows **clean architecture principles** with clear separation of concerns across layers.

## Architecture Principles

1. **Layered Architecture** - Clear separation between handlers, services, providers, and data layers
2. **Single Responsibility** - Each module has one well-defined purpose
3. **Dependency Inversion** - High-level modules don't depend on low-level modules
4. **DRY (Don't Repeat Yourself)** - Shared utilities extracted to reusable modules

## Project Structure

```
app/
├── main.py                    # Application entry point
│
├── config/
│   └── settings.py            # Environment variables & configuration
│
├── database/
│   └── session.py             # Database engine & session factory
│
├── models/                    # ORM models (SQLAlchemy)
│   ├── base.py
│   ├── user.py
│   ├── carrier.py
│   ├── tracking.py
│   └── tracking_event.py
│
├── handlers/                  # Telegram bot handlers (UI layer)
│   ├── base_handler.py        # Shared utilities for all handlers
│   ├── start_handler.py       # /start command
│   ├── help_handler.py        # /help, profile display
│   ├── language_handler.py    # Language selection
│   └── tracking_handler.py    # Tracking operations (add/list/remove)
│
├── services/                  # Business logic layer
│   └── tracking.py            # Tracking business logic
│
├── providers/                 # External API integrations
│   ├── base.py                # Base provider interface
│   ├── shopeeexpress/
│   │   ├── client.py          # Shopee Express API client
│   │   └── parser.py          # Response parser
│   └── jtexpress/
│       └── client.py          # JT Express API client
│
├── scheduler/
│   └── tracking.py            # Background job for checking updates
│
├── i18n/                      # Internationalization
│   ├── loader.py              # I18n loader logic
│   ├── en.json                # English translations
│   ├── vi.json                # Vietnamese translations
│   └── ja.json                # Japanese translations
│
├── constants/                 # Application constants
│   ├── enums.py               # Status enums, DTOs
│   ├── icons.py               # UI icons & display settings
│   └── user_state.py          # Conversation state constants
│
├── utils/                     # Utility functions
│   └── formatter.py           # UI formatting helpers
│
└── repositories/              # (Reserved for future DB layer)
```

## Layer Responsibilities

### 1. Handlers Layer (`app/handlers/`)

**Responsibility:** Handle Telegram updates, route commands, render UI

**Rules:**
- ✅ Receive user input (commands, callbacks, messages)
- ✅ Call service layer for business logic
- ✅ Use formatter utilities for rendering
- ❌ NO business logic
- ❌ NO direct database access
- ❌ NO external API calls

**Example:**
```python
async def list_command(self, update: Update, context: CallbackContext):
    trackings = self._service.list_trackings(chat_id)  # Call service
    text = formatter.render_list(trackings)             # Format UI
    await update.message.reply_text(text)               # Send response
```

### 2. Services Layer (`app/services/`)

**Responsibility:** Business logic, orchestration, data validation

**Rules:**
- ✅ Implement business rules
- ✅ Coordinate between providers and database
- ✅ Validate input data
- ✅ Return DTOs or domain models
- ❌ NO UI rendering
- ❌ NO Telegram-specific code

**Example:**
```python
def add_tracking(self, chat_id: int, tracking_code: str):
    # Validate
    carrier = self.detect_carrier(tracking_code)
    
    # Fetch from provider
    provider = self._provider_registry.get(carrier)
    history = provider.fetch_event_history(tracking_code)
    
    # Save to database
    tracking = Tracking(...)
    session.add(tracking)
    
    return tracking
```

### 3. Providers Layer (`app/providers/`)

**Responsibility:** External API integration, data fetching

**Rules:**
- ✅ Make HTTP requests to carrier APIs
- ✅ Parse responses into domain models
- ✅ Handle API-specific errors
- ❌ NO business logic
- ❌ NO database access

**Design Pattern:** Each provider is a self-contained module with:
- `client.py` - API communication
- `parser.py` - Response parsing (if complex)

### 4. Database Layer (`app/database/`, `app/models/`)

**Responsibility:** Data persistence, ORM models

**Rules:**
- ✅ Define database schema (models)
- ✅ Manage connections and sessions
- ❌ NO business logic

### 5. Utilities Layer (`app/utils/`)

**Responsibility:** Reusable helper functions

**Current utilities:**
- `formatter.py` - HTML formatting, datetime conversion, text escaping

## Data Flow

### User Request Flow
```
User Input (Telegram)
    ↓
Handler (routing, validation)
    ↓
Service (business logic)
    ↓
Provider (fetch data) + Database (persist)
    ↓
Service (process & return)
    ↓
Handler (format & render)
    ↓
User Response (Telegram)
```

### Background Scheduler Flow
```
APScheduler (every 5 minutes)
    ↓
TrackingScheduler._check_updates()
    ↓
Service._sync_tracking_history()
    ↓
Provider.fetch_event_history()
    ↓
Service (detect new events)
    ↓
Telegram Bot (send notifications)
```

## Key Design Decisions

### 1. Handler Split by Responsibility

**Before:** 1 monolithic `TrackingHandlers` class (900+ lines)

**After:** 5 focused handler classes
- `StartHandler` - Welcome screen
- `HelpHandler` - Help & profile
- `LanguageHandler` - Language selection
- `TrackingHandler` - Tracking operations
- `BaseHandler` - Shared utilities

**Benefits:**
- Easier to test individual features
- Clearer code ownership
- Reduced merge conflicts

### 2. Formatter Extraction

**Before:** Formatting logic mixed in handlers

**After:** Dedicated `utils/formatter.py`

**Benefits:**
- Handlers focus on routing
- Formatting logic reusable
- Easier to test UI rendering

### 3. Provider-Parser Cohesion

**Before:** Separate `parsers/` folder

**After:** Parser integrated with provider
```
providers/
  shopeeexpress/
    ├── client.py   # API calls
    └── parser.py   # Response parsing
```

**Benefits:**
- High cohesion (parser only used by its provider)
- Easier to add new carriers
- Clear module boundaries

### 4. State Constants

**Before:** Magic strings `"add_waiting_carrier"`

**After:** Constants in `constants/user_state.py`
```python
ADD_WAITING_CARRIER = "add_waiting_carrier"
```

**Benefits:**
- Avoid typos
- IDE autocomplete
- Easier refactoring

## Notification System

### Problem Solved
Scheduler was sending duplicate notifications for old events on every check.

### Solution
Track `last_event_hash` and only notify for events **after** the last known event:

```python
found_last_known = False
for event in history:
    if event.event_hash == last_known_hash:
        found_last_known = True
        continue
    
    # Only notify NEW events AFTER last known
    if notify and is_new and (last_known_hash is None or found_last_known):
        new_events.append(event)
```

## Database Schema

### Tables

**users**
- `id` (PK)
- `telegram_chat_id` (unique)
- `created_at`

**carriers**
- `id` (PK)
- `code` (unique) - e.g., "shopeeexpress", "jtexpress"
- `name` - Display name

**trackings**
- `id` (PK)
- `user_id` (FK → users)
- `carrier_id` (FK → carriers)
- `tracking_code`
- `last_status`
- `last_event_hash` - For detecting new events
- `next_check_at` - Scheduler optimization
- `is_active` - Soft delete

**tracking_events**
- `id` (PK)
- `tracking_id` (FK → trackings)
- `status`
- `description`
- `location`
- `event_time`
- `event_hash` (unique per tracking) - Deduplication

## Configuration

### Environment Variables (`.env`)

```bash
# Bot
BOT_TOKEN=your_telegram_bot_token
CHECK_INTERVAL_MINUTES=5

# Database
DATABASE_URL=mysql+pymysql://user:pass@host:3306/db

# Monitoring (optional)
SENTRY_DSN=your_sentry_dsn
LOG_LEVEL=INFO
```

## Deployment

### Docker Compose
```bash
docker compose up -d
```

**Services:**
- `bot` - Telegram bot application
- `mysql` - Database

### GitHub Actions
- **Quality Check** - Runs pylint, radon on every push
- **Deploy** - Auto-deploys to VPS on push to `main`

## Testing Strategy

### Unit Tests (Recommended)
- `services/` - Business logic
- `utils/formatter.py` - Formatting functions
- `providers/*/parser.py` - Response parsing

### Integration Tests (Recommended)
- Handler → Service → Database flow
- Provider API calls (with mocks)

### Manual Testing
- Use Telegram bot directly
- Check scheduler logs for notification behavior

## Future Improvements

### 1. Repository Layer
Extract database queries from services:
```
services/tracking.py → repositories/tracking_repo.py
```

### 2. Split Large Services
When `services/tracking.py` grows:
```
services/
  ├── tracking_create.py
  ├── tracking_query.py
  └── tracking_update.py
```

### 3. DTO Layer
Formalize data transfer objects:
```python
@dataclass
class TrackingDetailDTO:
    tracking_code: str
    carrier_name: str
    status: str
    events: list[EventDTO]
```

### 4. Caching Layer
Add Redis for:
- Rate limiting API calls
- Caching tracking history
- Reducing database load

### 5. Event Sourcing
Store all state changes for:
- Audit trail
- Debugging
- Analytics

## Monitoring & Observability

### Logging
- **INFO** - Normal operations (scheduler ticks, notifications sent)
- **WARNING** - Recoverable errors (API timeouts, invalid tracking codes)
- **ERROR** - Unexpected failures (database errors, unhandled exceptions)

### Metrics to Track
- Active trackings count
- Notification delivery rate
- API response times
- Scheduler execution time

### Sentry Integration
Automatic error reporting for:
- Unhandled exceptions
- Telegram API errors
- Provider API failures

## Contributing Guidelines

### Adding a New Carrier

1. Create provider module:
```
app/providers/newcarrier/
  ├── __init__.py
  ├── client.py
  └── parser.py  (if needed)
```

2. Implement `TrackingProvider` interface:
```python
class NewCarrierProvider(TrackingProvider):
    carrier_code = "newcarrier"
    
    def fetch_event_history(self, tracking_code: str):
        # Implementation
```

3. Register in `providers/__init__.py`:
```python
def build_provider_registry():
    return {
        "shopeeexpress": ShopeeExpressProvider(),
        "jtexpress": JTExpressProvider(),
        "newcarrier": NewCarrierProvider(),  # Add here
    }
```

4. Update `services/tracking.py`:
```python
SUPPORTED_CARRIERS = {
    "newcarrier": "New Carrier Name",
    # ...
}
```

### Code Style

- Follow PEP 8
- Use type hints
- Keep functions < 50 lines
- Keep files < 500 lines
- Use `%s` format in logger calls (not f-strings)

## License

MIT License - See LICENSE file for details
