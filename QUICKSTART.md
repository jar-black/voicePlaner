# Quick Start Guide

Get the AI Project Orchestrator running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Anthropic API key ([get one here](https://console.anthropic.com/))
- GitHub Personal Access Token ([create one here](https://github.com/settings/tokens))

## Step 1: Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd ai-project-orchestrator

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your favorite editor
```

Set these required values in `.env`:
```env
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
```

## Step 2: Start Services

```bash
docker-compose up -d
```

Wait about 30 seconds for all services to start.

## Step 3: Verify Installation

```bash
curl http://localhost:8000/health
```

You should see:
```json
{
  "status": "healthy",
  "database": true,
  "claude": true,
  "mcp_servers": {
    "planning": true,
    "github": true,
    "claude_code": true
  }
}
```

## Step 4: Create Your First Project

### Option A: Using CLI

```bash
# Install CLI dependencies
cd cli
pip install -r requirements.txt

# Create a project
python cli.py create "Build a todo list app with React frontend and FastAPI backend"
```

Follow the conversation with Claude, then:

```bash
# When ready, finalize
python cli.py finalize <project-id>

# View the plan
python cli.py plan <project-id>
```

### Option B: Using API

```bash
# Create project
curl -X POST http://localhost:8000/projects/create \
  -H "Content-Type: application/json" \
  -d '{"initial_description": "Build a todo list app with React frontend and FastAPI backend"}'

# Save the project_id from response

# Continue conversation
curl -X POST http://localhost:8000/projects/continue \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<project-id>",
    "message": "Add user authentication and PostgreSQL database"
  }'

# When ready to finalize
curl -X POST http://localhost:8000/projects/finalize \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<project-id>",
    "create_github_repo": true,
    "create_issues": true
  }'
```

## Step 5: Check Your GitHub

After finalization, check your GitHub account:
- New repository created
- Project structure initialized
- Issues created for all tasks

## Next Steps

- View API documentation: http://localhost:8000/docs
- Read the full README for advanced features
- Explore MCP server APIs:
  - Planning: http://localhost:8002/tools
  - GitHub: http://localhost:8001/tools
  - Claude Code: http://localhost:8003/tools

## Common Issues

### Services not starting?

```bash
# Check logs
docker-compose logs

# Restart
docker-compose restart
```

### Database errors?

```bash
# Reset database
docker-compose down -v
docker-compose up -d
```

### API not responding?

```bash
# Check if ports are available
netstat -an | grep 8000

# Try different ports in docker-compose.yml
```

## Example Conversation Flow

```
You: "Build a todo list app with React frontend and FastAPI backend"

Claude: "Great! I've analyzed your project. Here's what I understand:
- Project Name: Todo List Application
- Type: Full-stack web application
- Complexity: Moderate

I have a few questions:
1. Do you want user authentication?
2. Should todos be shareable between users?
3. Any specific features like deadlines, categories, or priorities?"

You: "Yes to authentication, no sharing needed. Add deadlines and priority levels."

Claude: "Perfect! I now have enough information. The project is ready to finalize.
I've structured it into 5 epics with 15 user stories and 45 implementation tasks."

[Run finalize command]

Result: GitHub repo created with all tasks as issues, ready to start coding!
```

## Tips

1. **Be specific in initial description**: Include tech stack, main features
2. **Answer Claude's questions thoroughly**: Better info = better plan
3. **Review the plan before finalizing**: Use `cli.py plan <id>` to preview
4. **Start with smaller projects**: Get familiar with the workflow
5. **Use the API docs**: http://localhost:8000/docs for interactive testing

## Getting Help

- Check the full README.md for detailed documentation
- View logs: `docker-compose logs -f`
- API reference: http://localhost:8000/docs
- Database access: `docker-compose exec db psql -U projectuser -d projects`

Happy building! 🚀
