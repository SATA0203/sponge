"""
Sponge - Multi-Agent Collaborative Code Development System

## Overview

**Sponge** is an intelligent code development system that leverages multiple AI agents working collaboratively to analyze requirements, write code, review implementations, run tests, and deploy applications.

## Key Features

- 🤖 **Multi-Agent Collaboration**: Specialized agents for planning, coding, reviewing, testing, and deployment
- 🔄 **Automated Workflows**: LangGraph-powered state machines for complex task orchestration
- 🛡️ **Secure Execution**: Docker-based sandbox for safe code execution
- ⚡ **Async Processing**: Celery-based task queue for parallel agent operations
- 📊 **Real-time Monitoring**: Comprehensive logging and status tracking
- 🔌 **Extensible Architecture**: Easy to add new agents, tools, and workflows

## Quick Start

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Node.js 16+ (optional, for frontend)

### Installation

```bash
# Clone the repository
cd sponge

# Copy environment configuration
cp .env.example .env

# Edit .env with your API keys
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_key_here

# Start with Docker Compose
docker-compose up -d

# Access API documentation
open http://localhost:8000/docs
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start infrastructure services
docker-compose up -d postgres redis

# Run API server
uvicorn app.main:app --reload

# Run Celery worker
celery -A app.celery_app worker --loglevel=info
```

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                    │
└────────────────────┬────────────────────────────────┘
                     │ REST API / WebSocket
┌────────────────────▼────────────────────────────────┐
│                  FastAPI Server                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Tasks   │  │  Files   │  │  Health  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│               Celery Task Queue                      │
│         (Async Agent Coordination)                   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│              LangGraph Workflow Engine               │
│  ┌──────────────────────────────────────────────┐   │
│  │  Planner → Coder → Reviewer → Tester        │   │
│  │       ↑                              ↓       │   │
│  │       └────────── Iteration ──────────┘      │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│                Tools & Sandboxes                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │  Files   │  │  Code    │  │  Docker  │          │
│  │  Tools   │  │ Executor │  │ Sandbox │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

## Project Structure

```
sponge/
├── app/
│   ├── main.py              # FastAPI application
│   ├── celery_app.py        # Celery configuration
│   ├── core/                # Core settings & config
│   ├── schemas/             # Pydantic models
│   ├── agents/              # Agent implementations
│   ├── tools/               # Utility tools
│   ├── workflow/            # LangGraph workflows
│   └── api/                 # API routers
├── tests/                   # Test suite
├── docker-compose.yml       # Service orchestration
├── requirements.txt         # Python dependencies
└── DEVELOPMENT.md           # Development guide
```

## API Endpoints

### Tasks
- `POST /api/v1/tasks/` - Create new task
- `GET /api/v1/tasks/` - List tasks
- `GET /api/v1/tasks/{id}` - Get task details
- `POST /api/v1/tasks/{id}/cancel` - Cancel task
- `DELETE /api/v1/tasks/{id}` - Delete task

### Files
- `GET /api/v1/files/` - List files
- `GET /api/v1/files/content` - Get file content
- `POST /api/v1/files/update` - Update file
- `GET /api/v1/files/exists` - Check file exists

### Health
- `GET /health/` - Health check
- `GET /health/ready` - Readiness check
- `GET /health/live` - Liveness check

## Documentation

### Quick Start
- [Getting Started](GET_STARTED.md) - Environment setup and installation
- [Development Guide](DEVELOPMENT.md) - Development workflow and best practices

### Technical Documentation
- [API Reference](docs/API_REFERENCE.md) - Complete REST API documentation
- [Architecture](docs/ARCHITECTURE.md) - System architecture and design
- [Multi-Agent Guide](docs/MULTI_AGENT_GUIDE.md) - Agent collaboration details
- [Documentation Index](docs/README.md) - Navigate all documentation

### Project Documents
- [PRD](PRD_SpongeCodeAgent.md) - Product requirements document
- [Progress](PROGRESS.md) - Current development status

## Technology Stack

- **Backend**: FastAPI, Python 3.11
- **Workflow**: LangGraph, LangChain
- **Task Queue**: Celery, Redis
- **Database**: PostgreSQL
- **Sandbox**: Docker
- **LLM**: OpenAI GPT-4, Anthropic Claude

## Roadmap

### Phase 1 (MVP) - Current
- [x] Project scaffolding
- [x] Core configuration
- [x] API structure
- [x] File tools
- [ ] Agent implementations
- [ ] Workflow engine
- [ ] Code executor

### Phase 2
- [ ] Database integration
- [ ] Advanced code analysis
- [ ] Test generation
- [ ] CI/CD integration

### Phase 3
- [ ] Web UI
- [ ] Plugin system
- [ ] Multi-language support
- [ ] Team collaboration

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- GitHub Issues: Report bugs and feature requests
- Documentation: Check DEVELOPMENT.md and other docs

---

**Sponge** - Absorbing complexity, expelling code.
