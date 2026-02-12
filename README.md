# LeetCode Reminder Bot 🚀

> **Production-ready Telegram bot** for LeetCode daily reminders with Clean Architecture, PostgreSQL, FastAPI, Celery, and comprehensive CI/CD pipeline.

[![CI/CD](https://github.com/yourusername/leetcode-reminder/actions/workflows/ci.yml/badge.svg)](https://github.com/yourusername/leetcode-reminder/actions)
[![Code Quality](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Security](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Development](#development)
- [Production Deployment](#production-deployment)
- [API Documentation](#api-documentation)
- [Security](#security)
- [Monitoring & Logging](#monitoring--logging)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

LeetCode Reminder Bot is a sophisticated Telegram bot that helps users maintain their daily LeetCode practice streak. It features:

- **Intelligent Scheduling**: Celery Beat for efficient API request management
- **Clean Architecture**: Separation of concerns with domain-driven design
- **Dual Storage**: Redis (fast) + PostgreSQL (persistent)
- **Production-Ready API**: FastAPI with rate limiting, security, and comprehensive error handling
- **CI/CD Pipeline**: Automated testing, linting, security scanning, and deployment
- **Enterprise Security**: Rate limiting, input validation, CORS, trusted hosts

## 🏗️ Architecture

### Clean Architecture Layers

```
app/
├── api/                    # FastAPI Clean Architecture
│   ├── domain/            # Business entities & repository interfaces
│   ├── use_cases/         # Business logic
│   ├── infrastructure/     # Repository implementations
│   └── interfaces/        # Controllers, schemas, dependencies
├── bot.py                 # Telegram bot application
├── celery_app.py          # Celery configuration
├── celery_tasks.py        # Background tasks
├── scheduler.py           # Bot scheduler
├── leetcode.py            # LeetCode API client
├── storage.py             # Redis + PostgreSQL storage
└── database.py            # PostgreSQL models
```

### System Architecture

```
┌─────────────────┐
│  Telegram Bot   │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Redis  │◄───┐
    └────┬────┘    │
         │         │
    ┌────┴────┐    │
    │PostgreSQL│   │
    └────┬────┘    │
         │         │
    ┌────┴────┐    │
    │ FastAPI  │   │
    └────┬────┘    │
         │         │
    ┌────┴────┐    │
    │ Celery  │────┘
    │ Worker  │
    └─────────┘
```

## ✨ Features

### Core Features

- ✅ **Daily Reminders**: Customizable reminder times per user
- ✅ **LeetCode Integration**: Real-time submission checking via GraphQL API
- ✅ **Timezone Support**: Per-user timezone configuration
- ✅ **Smart Throttling**: Celery-based request management to avoid API rate limits
- ✅ **Dual Storage**: Redis for fast access + PostgreSQL for persistence
- ✅ **REST API**: Comprehensive FastAPI with OpenAPI documentation

### Production Features

- 🔒 **Security**: Rate limiting, input validation, CORS, trusted hosts
- 📊 **Monitoring**: Structured logging, health checks, metrics
- 🚀 **CI/CD**: Automated testing, linting, security scanning, deployment
- 🐳 **Docker**: Multi-container setup with docker-compose
- 📝 **Code Quality**: Pre-commit hooks, type checking, code formatting

## 🛠️ Tech Stack

### Backend
- **Python 3.11+**
- **python-telegram-bot**: Telegram Bot API
- **FastAPI**: Modern, fast web framework
- **SQLAlchemy**: ORM for PostgreSQL
- **Celery**: Distributed task queue
- **Redis**: Caching and message broker
- **PostgreSQL**: Primary database

### DevOps & Tools
- **Docker & Docker Compose**: Containerization
- **GitHub Actions**: CI/CD pipeline
- **Pre-commit**: Git hooks for code quality
- **Black, isort, flake8**: Code formatting and linting
- **MyPy**: Static type checking
- **Bandit**: Security linting
- **Pytest**: Testing framework

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (recommended)
- PostgreSQL 15+ (if not using Docker)
- Redis 7+ (if not using Docker)

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/leetcode-reminder.git
cd leetcode-reminder
```

2. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env and configure your settings
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Set up pre-commit hooks**

```bash
pip install pre-commit
pre-commit install
```

5. **Run with Docker Compose** (Recommended)

```bash
docker-compose up -d
```

This will start:
- Redis
- PostgreSQL
- Bot
- FastAPI
- Celery Worker
- Celery Beat

### Manual Setup

1. **Start Redis and PostgreSQL**

```bash
# Redis
redis-server

# PostgreSQL
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=leetcode_bot \
  -p 5432:5432 \
  postgres:15
```

2. **Run the bot**

```bash
python -m app.bot
```

3. **Run API server** (separate terminal)

```bash
python -m app.api_server
```

4. **Run Celery Worker** (separate terminal)

```bash
celery -A app.celery_app worker --loglevel=info
```

5. **Run Celery Beat** (separate terminal)

```bash
celery -A app.celery_app beat --loglevel=info
```

## 💻 Development

### Project Structure

```
leetcode-reminder/
├── .github/
│   └── workflows/          # CI/CD pipelines
├── app/
│   ├── api/               # FastAPI Clean Architecture
│   │   ├── domain/        # Domain entities & interfaces
│   │   ├── use_cases/     # Business logic
│   │   ├── infrastructure/# Implementations
│   │   └── interfaces/    # API layer
│   ├── bot.py             # Telegram bot
│   ├── celery_*.py        # Celery configuration
│   ├── config.py          # Settings management
│   ├── database.py        # PostgreSQL models
│   ├── leetcode.py        # LeetCode API client
│   ├── scheduler.py       # Bot scheduler
│   └── storage.py         # Storage abstraction
├── tests/                 # Test suite
├── .pre-commit-config.yaml
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Code Quality

The project uses multiple tools for code quality:

```bash
# Format code
black app/ --line-length=100

# Sort imports
isort app/ --profile black

# Lint
flake8 app/

# Type check
mypy app/

# Security check
bandit -r app/ -ll
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov pytest-asyncio

# Run tests
pytest tests/ -v --cov=app --cov-report=html
```

### Pre-commit Hooks

Pre-commit hooks automatically run on `git commit`:

- Code formatting (Black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- YAML/JSON validation

## 🚢 Production Deployment

### Environment Variables

```bash
# Required
BOT_TOKEN=your_telegram_bot_token
REDIS_URL=redis://redis:6379/0
POSTGRESQL_URL=postgresql://user:password@host:5432/dbname

# Optional
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
API_KEY=your-secure-api-key
ALLOWED_HOSTS=yourdomain.com
CORS_ORIGINS=https://yourdomain.com
```

### Docker Production

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Gunicorn Production Server

```bash
gunicorn app.api_app:app \
  --config gunicorn_config.py \
  --workers 4 \
  --bind 0.0.0.0:8000
```

### Systemd Service (Linux)

Create `/etc/systemd/system/leetcode-bot.service`:

```ini
[Unit]
Description=LeetCode Reminder Bot
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=youruser
WorkingDirectory=/opt/leetcode-reminder
Environment="PATH=/opt/leetcode-reminder/venv/bin"
ExecStart=/opt/leetcode-reminder/venv/bin/python -m app.bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 📚 API Documentation

### Base URL

```
http://localhost:8000
```

### Endpoints

#### Health Check

```http
GET /api/health
```

#### Get All Users

```http
GET /api/users?active_only=true&limit=10&offset=0
```

#### Get User by Telegram ID

```http
GET /api/users/telegram/{telegram_id}
```

#### Get Users by LeetCode Username

```http
GET /api/users/leetcode/{leetcode_username}
```

#### Get Statistics

```http
GET /api/stats
```

### Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Rate Limits

- **Default**: 60 requests/minute per IP
- **Health endpoint**: 30 requests/minute
- **Stats endpoint**: 30 requests/minute

## 🔒 Security

### Implemented Security Measures

1. **Rate Limiting**: Per-IP rate limiting using SlowAPI
2. **Input Validation**: Pydantic models for all inputs
3. **CORS**: Configurable CORS middleware
4. **Trusted Hosts**: Host validation middleware
5. **API Key Authentication**: Optional API key support
6. **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
7. **XSS Prevention**: Input sanitization and validation
8. **Security Headers**: FastAPI security middleware

### Security Best Practices

- ✅ Never commit `.env` files
- ✅ Use strong API keys (32+ characters)
- ✅ Enable HTTPS in production
- ✅ Regular dependency updates
- ✅ Security scanning in CI/CD
- ✅ Rate limiting on all endpoints
- ✅ Input validation on all inputs

### Security Scanning

```bash
# Bandit security scan
bandit -r app/ -ll

# Trivy vulnerability scan (Docker)
trivy image your-image:tag
```

## 📊 Monitoring & Logging

### Logging

Logs are structured and include:

- Timestamp
- Log level
- Module name
- Message
- File location (for errors)

### Log Levels

- `DEBUG`: Detailed debugging information
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

### Health Checks

```bash
# API health
curl http://localhost:8000/api/health

# Bot health (check logs)
docker-compose logs bot
```

### Metrics

Key metrics to monitor:

- API request rate
- Celery task execution time
- Database connection pool usage
- Redis memory usage
- Error rates
- Response times

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run pre-commit hooks (`pre-commit run --all-files`)
5. Write tests for new features
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write docstrings for all functions/classes
- Add type hints
- Write tests for new features
- Update documentation
- Keep commits atomic and descriptive

## 📝 Bot Commands

- `/start` - Start bot and register user
- `/setusername <username>` - Set LeetCode username
- `/check` - Check if solved today
- `/status` - Get current status
- `/listremind` - List reminder times
- `/setremind <HH:MM>` - Set reminder time
- `/addremind <HH:MM>` - Add reminder time
- `/delremind <HH:MM>` - Delete reminder time
- `/timezone <tz>` - Set timezone (e.g., Asia/Tashkent)
- `/help` - Show help message

## 🐛 Troubleshooting

### Common Issues

**Bot not responding**
- Check bot token in `.env`
- Verify Redis is running
- Check bot logs: `docker-compose logs bot`
- After deploy/restart, monitor for 2-5 minutes: `docker compose logs -f bot`

**API not accessible**
- Verify PostgreSQL connection
- Check API logs: `docker-compose logs api`
- Ensure port 8000 is not blocked

**Celery tasks not running**
- Check Celery worker: `docker-compose logs celery_worker`
- Verify Redis connection
- Check Celery Beat: `docker-compose logs celery_beat`

**Database connection errors**
- Verify PostgreSQL is running
- Check connection string in `.env`
- Ensure database exists
- Ensure `.env` has matching DB vars: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`
- If password/auth keeps failing with old data, recreate DB volume: `docker compose down -v && docker compose up -d`

**`/check` or `/status` gives LeetCode API errors**
- This can happen when LeetCode returns non-JSON (Cloudflare/challenge page) even with status 200
- Try again after a few minutes (temporary upstream block/rate limit)
- Verify server clock and timezone are correct (NTP enabled)
- Monitor logs: `docker compose logs -f bot`
- If this repeats often on your server IP, add a fallback provider for LeetCode checks

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- LeetCode for the GraphQL API
- python-telegram-bot community
- FastAPI team
- All contributors

## 📞 Support

For issues, questions, or contributions:

- **Issues**: [GitHub Issues](https://github.com/yourusername/leetcode-reminder/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/leetcode-reminder/discussions)

---

**Made with ❤️ for the LeetCode community**
