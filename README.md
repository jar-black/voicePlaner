# AI Project Orchestrator

An intelligent system that uses Claude AI to orchestrate the complete lifecycle of software project creation, from initial idea to production-ready implementation.

## Overview

The AI Project Orchestrator is a sophisticated platform that automates software project planning, structuring, and execution. It combines Claude AI's natural language understanding with specialized MCP (Model Context Protocol) servers to create a seamless workflow for software development.

### Key Features

- **AI-Powered Project Planning**: Have natural conversations with Claude to refine your project idea into a structured plan
- **Automated Project Structure**: Automatically generates epics, user stories, and technical tasks
- **GitHub Integration**: Creates repositories, project structure, and issues automatically
- **Claude Code Integration**: Seamlessly hands off implementation tasks to Claude Code
- **Database-Backed Tracking**: PostgreSQL database tracks all projects, conversations, and execution status
- **RESTful API**: Full-featured API for integration with other tools
- **CLI Interface**: User-friendly command-line interface for quick interactions

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  User Interface                          │
│              (CLI / API / Web)                           │
└─────────────────┬────────────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────────────┐
│           Orchestrator Service (FastAPI)                 │
│  - Claude API Integration                                │
│  - Conversation Management                               │
│  - MCP Client Coordination                               │
└─────────────────┬────────────────────────────────────────┘
                  │
                  │ MCP Protocol (REST APIs)
                  │
    ┌─────────────┼─────────────┬──────────────┐
    │             │             │              │
┌───▼────┐   ┌───▼────┐   ┌───▼────┐   ┌────▼─────┐
│Project │   │ GitHub │   │ Claude │   │PostgreSQL│
│Planning│   │  MCP   │   │  Code  │   │ Database │
│  MCP   │   │ Server │   │  MCP   │   │          │
└────────┘   └────────┘   └────────┘   └──────────┘
```

### Components

1. **Orchestrator Service** (`orchestrator/`)
   - Main FastAPI application
   - Manages conversations with Claude AI
   - Coordinates MCP servers
   - Handles project lifecycle

2. **Project Planning MCP Server** (`mcp-servers/project-planning-mcp/`)
   - Manages project structure (Epics, Stories, Tasks)
   - PostgreSQL integration
   - Query and reporting tools

3. **GitHub MCP Server** (`mcp-servers/github-mcp/`)
   - Repository creation and management
   - Issue creation from tasks
   - Project structure initialization
   - Label management

4. **Claude Code MCP Server** (`mcp-servers/claude-code-mcp/`)
   - Integration with Claude Code CLI
   - Task execution management
   - Git workflow automation

5. **CLI Interface** (`cli/`)
   - User-friendly command-line interface
   - Rich text formatting
   - Interactive workflows

## Installation

### Prerequisites

- Docker and Docker Compose
- Anthropic API key
- GitHub Personal Access Token (for GitHub integration)

### Quick Start

1. **Clone the repository**

```bash
git clone <repository-url>
cd ai-project-orchestrator
```

2. **Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` and set:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
GITHUB_TOKEN=your_github_token
GITHUB_ORG=your_github_org  # Optional
```

3. **Start the services**

```bash
docker-compose up -d
```

This will start:
- Orchestrator API (port 8000)
- Project Planning MCP (port 8002)
- GitHub MCP (port 8001)
- Claude Code MCP (port 8003)
- PostgreSQL database (port 5432)

4. **Verify services are running**

```bash
curl http://localhost:8000/health
```

## Usage

### Using the CLI

Install the CLI dependencies:

```bash
cd cli
pip install -r requirements.txt
```

#### Create a New Project

```bash
python cli.py create "I want to build a task management web app with React and FastAPI"
```

This initiates a conversation with Claude. You'll receive:
- Project name suggestion
- Technology stack recommendations
- Initial feature breakdown
- Clarifying questions

#### Continue the Conversation

```bash
python cli.py continue <project-id> "Yes, use PostgreSQL for the database and add user authentication"
```

Keep refining until Claude indicates the project is ready to finalize.

#### Finalize the Project

```bash
python cli.py finalize <project-id>
```

This will:
- Generate complete project structure
- Create GitHub repository
- Set up project files
- Create GitHub issues for all tasks
- Initialize Claude Code workspace

#### View Project Plan

```bash
python cli.py plan <project-id>
```

#### List All Projects

```bash
python cli.py list
```

#### Get Next Tasks

```bash
python cli.py tasks <project-id> --limit 5
```

### Using the API

#### Create a Project

```bash
curl -X POST http://localhost:8000/projects/create \
  -H "Content-Type: application/json" \
  -d '{
    "initial_description": "Build a real-time chat application with WebSockets"
  }'
```

#### Continue Conversation

```bash
curl -X POST http://localhost:8000/projects/continue \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "uuid-here",
    "message": "Add support for file attachments and emoji reactions"
  }'
```

#### Finalize Project

```bash
curl -X POST http://localhost:8000/projects/finalize \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "uuid-here",
    "create_github_repo": true,
    "create_issues": true
  }'
```

#### Get Project Plan

```bash
curl http://localhost:8000/projects/{project-id}/plan
```

## Workflow

### 1. Project Creation Phase

User describes their project idea in natural language. Claude analyzes and extracts:
- Project name and type
- Technology stack
- Initial feature ideas
- Complexity assessment

### 2. Refinement Phase

Through conversation, Claude asks clarifying questions about:
- Core features and requirements
- Technical architecture preferences
- User stories and acceptance criteria
- Priority and scope

### 3. Finalization Phase

Once sufficient information is gathered:
- Generate structured project plan (Epics → Stories → Tasks)
- Create database records for all components
- Set up GitHub repository with project structure
- Create GitHub issues for all tasks
- Initialize Claude Code workspace

### 4. Execution Phase

Tasks are prioritized and can be executed:
- Manual execution via GitHub issues
- Automated execution via Claude Code integration
- Progress tracking and status updates

## Database Schema

### Core Tables

- **projects**: Top-level project information
- **epics**: High-level feature groupings
- **stories**: User stories implementing epics
- **tasks**: Individual technical tasks implementing stories
- **conversations**: AI conversation history
- **execution_logs**: Task execution tracking

### Relationships

```
projects
  ↓
epics
  ↓
stories
  ↓
tasks
```

Each level maintains status, priority, and ordering information.

## API Reference

### Main Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/projects/create` | POST | Create new project |
| `/projects/continue` | POST | Continue conversation |
| `/projects/finalize` | POST | Finalize and create resources |
| `/projects/{id}` | GET | Get project details |
| `/projects/{id}/plan` | GET | Get complete project plan |
| `/projects/{id}/next-tasks` | GET | Get prioritized tasks |
| `/projects` | GET | List all projects |
| `/tasks/execute` | POST | Execute a task |
| `/health` | GET | Health check |

### MCP Server APIs

Each MCP server exposes:
- `/health` - Health check
- `/tools` - List available tools
- `/call_tool` - Execute a tool

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `GITHUB_TOKEN` | GitHub personal access token | Yes (for GitHub features) |
| `GITHUB_ORG` | GitHub organization name | No |
| `DATABASE_URL` | PostgreSQL connection URL | Yes |
| `CLAUDE_MODEL` | Claude model to use | No (default: claude-sonnet-4-5-20250929) |

### Docker Compose Customization

Edit `docker-compose.yml` to:
- Change port mappings
- Adjust resource limits
- Configure volumes
- Set environment variables

## Development

### Local Development Setup

1. **Set up Python environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies**

```bash
# For orchestrator
cd orchestrator && pip install -r requirements.txt

# For MCP servers
cd ../mcp-servers/project-planning-mcp && pip install -r requirements.txt
cd ../github-mcp && pip install -r requirements.txt
cd ../claude-code-mcp && pip install -r requirements.txt
```

3. **Start PostgreSQL**

```bash
docker-compose up -d db
```

4. **Run services individually**

```bash
# Terminal 1: Orchestrator
cd orchestrator && python main.py

# Terminal 2: Planning MCP
cd mcp-servers/project-planning-mcp && python server.py

# Terminal 3: GitHub MCP
cd mcp-servers/github-mcp && python server.py

# Terminal 4: Claude Code MCP
cd mcp-servers/claude-code-mcp && python server.py
```

### Testing

```bash
# Test orchestrator health
curl http://localhost:8000/health

# Test MCP servers
curl http://localhost:8002/health  # Planning MCP
curl http://localhost:8001/health  # GitHub MCP
curl http://localhost:8003/health  # Claude Code MCP
```

## Project Structure

```
ai-project-orchestrator/
├── docker-compose.yml          # Docker services configuration
├── .env.example                # Environment variables template
├── README.md                   # This file
│
├── orchestrator/               # Main orchestration service
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                # FastAPI application
│   ├── config.py              # Configuration management
│   ├── models/                # Pydantic models
│   │   └── project.py
│   └── services/              # Business logic
│       ├── claude_service.py
│       └── mcp_client.py
│
├── mcp-servers/               # MCP server implementations
│   ├── project-planning-mcp/  # Project structure management
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py
│   ├── github-mcp/            # GitHub integration
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py
│   └── claude-code-mcp/       # Claude Code integration
│       ├── Dockerfile
│       ├── requirements.txt
│       └── server.py
│
├── database/                  # Database configuration
│   └── init.sql              # Schema initialization
│
└── cli/                      # Command-line interface
    ├── requirements.txt
    └── cli.py
```

## Use Cases

### 1. Solo Developer

Start a new project with AI assistance:
1. Describe your idea in natural language
2. Refine through conversation
3. Get a complete project plan
4. Have GitHub repo and issues created
5. Start implementing tasks

### 2. Team Lead

Plan and structure a team project:
1. Collaborate with Claude to define project scope
2. Generate comprehensive epic/story breakdown
3. Create GitHub issues for team assignment
4. Track progress through the system

### 3. Product Manager

Convert product vision to technical plan:
1. Describe product requirements
2. Claude helps define user stories and acceptance criteria
3. Technical tasks generated automatically
4. Export to GitHub for development team

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs orchestrator
docker-compose logs planning-mcp

# Restart services
docker-compose restart
```

### Database connection issues

```bash
# Check database is running
docker-compose ps db

# Verify connection
docker-compose exec db psql -U projectuser -d projects -c "SELECT 1;"
```

### MCP servers not responding

```bash
# Check MCP server health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# View logs
docker-compose logs github-mcp
docker-compose logs planning-mcp
docker-compose logs claude-code-mcp
```

## Limitations

- Claude Code integration requires manual execution steps (fully automated execution coming soon)
- GitHub organization support requires appropriate permissions
- Large projects may require conversation context management
- Real-time collaboration features not yet implemented

## Future Enhancements

- [ ] Web UI for project management
- [ ] Real-time WebSocket updates
- [ ] Team collaboration features
- [ ] Advanced analytics and reporting
- [ ] Integration with more development tools
- [ ] Automated testing generation
- [ ] CI/CD pipeline generation
- [ ] Multi-repository project support

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check documentation at `/docs` endpoint
- Review API reference at `/docs` (Swagger UI)

## Acknowledgments

- Built with Claude AI by Anthropic
- Uses the Model Context Protocol (MCP)
- FastAPI framework
- PostgreSQL database
- Docker containerization

---

**Built with ❤️ and AI**
