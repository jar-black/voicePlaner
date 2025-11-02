#!/usr/bin/env python3
"""
AI Project Orchestrator CLI
"""

import click
import httpx
import json
from rich.console import Console
from rich.table import Table
from rich.markdown import Markdown
from rich.panel import Panel
from typing import Optional

console = Console()

DEFAULT_API_URL = "http://localhost:8000"


class OrchestratorClient:
    """Client for interacting with the Orchestrator API"""

    def __init__(self, api_url: str = DEFAULT_API_URL):
        self.api_url = api_url
        self.client = httpx.Client(timeout=60.0)

    def create_project(self, description: str):
        """Create a new project"""
        response = self.client.post(
            f"{self.api_url}/projects/create",
            json={"initial_description": description}
        )
        response.raise_for_status()
        return response.json()

    def continue_conversation(self, project_id: str, message: str):
        """Continue project conversation"""
        response = self.client.post(
            f"{self.api_url}/projects/continue",
            json={"project_id": project_id, "message": message}
        )
        response.raise_for_status()
        return response.json()

    def finalize_project(
        self,
        project_id: str,
        create_github: bool = True,
        create_issues: bool = True
    ):
        """Finalize project"""
        response = self.client.post(
            f"{self.api_url}/projects/finalize",
            json={
                "project_id": project_id,
                "create_github_repo": create_github,
                "create_issues": create_issues
            }
        )
        response.raise_for_status()
        return response.json()

    def get_project(self, project_id: str):
        """Get project details"""
        response = self.client.get(f"{self.api_url}/projects/{project_id}")
        response.raise_for_status()
        return response.json()

    def get_project_plan(self, project_id: str):
        """Get project plan"""
        response = self.client.get(f"{self.api_url}/projects/{project_id}/plan")
        response.raise_for_status()
        return response.json()

    def list_projects(self, status: Optional[str] = None):
        """List projects"""
        params = {"status": status} if status else {}
        response = self.client.get(f"{self.api_url}/projects", params=params)
        response.raise_for_status()
        return response.json()

    def get_next_tasks(self, project_id: str, limit: int = 5):
        """Get next tasks"""
        response = self.client.get(
            f"{self.api_url}/projects/{project_id}/next-tasks",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()


@click.group()
@click.option('--api-url', default=DEFAULT_API_URL, help='Orchestrator API URL')
@click.pass_context
def cli(ctx, api_url):
    """AI Project Orchestrator CLI"""
    ctx.ensure_object(dict)
    ctx.obj['client'] = OrchestratorClient(api_url)


@cli.command()
@click.argument('description')
@click.pass_context
def create(ctx, description):
    """Create a new project with initial description"""
    client = ctx.obj['client']

    console.print("[bold blue]Creating new project...[/bold blue]")

    try:
        result = client.create_project(description)

        console.print(f"\n[bold green]Project created![/bold green]")
        console.print(f"[yellow]Project ID:[/yellow] {result['project_id']}")
        console.print(f"[yellow]Project Name:[/yellow] {result['project_name']}")
        console.print(f"[yellow]Status:[/yellow] {result['status']}\n")

        console.print(Panel(Markdown(result['response']), title="Claude's Response"))

        console.print(f"\n[dim]Continue the conversation with:[/dim]")
        console.print(f"[dim]  orchestrator continue {result['project_id']} \"your message\"[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.argument('project_id')
@click.argument('message')
@click.pass_context
def continue_chat(ctx, project_id, message):
    """Continue refining the project"""
    client = ctx.obj['client']

    console.print("[bold blue]Sending message...[/bold blue]")

    try:
        result = client.continue_conversation(project_id, message)

        console.print(Panel(Markdown(result['response']), title="Claude's Response"))

        if result['ready_to_finalize']:
            console.print("\n[bold green]Project is ready to finalize![/bold green]")
            console.print(f"[dim]Run: orchestrator finalize {project_id}[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.argument('project_id')
@click.option('--no-github', is_flag=True, help='Skip GitHub repository creation')
@click.option('--no-issues', is_flag=True, help='Skip GitHub issues creation')
@click.pass_context
def finalize(ctx, project_id, no_github, no_issues):
    """Finalize project and create all resources"""
    client = ctx.obj['client']

    console.print("[bold blue]Finalizing project...[/bold blue]")
    console.print("[dim]This may take a minute...[/dim]\n")

    try:
        result = client.finalize_project(
            project_id,
            create_github=not no_github,
            create_issues=not no_issues
        )

        console.print("[bold green]Project finalized successfully![/bold green]\n")

        if result.get('github_repo_url'):
            console.print(f"[yellow]GitHub Repository:[/yellow] {result['github_repo_url']}")

        console.print(f"[yellow]Epics Created:[/yellow] {result['epic_count']}")
        console.print(f"\n[dim]View project plan with:[/dim]")
        console.print(f"[dim]  orchestrator plan {project_id}[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.argument('project_id')
@click.pass_context
def show(ctx, project_id):
    """Show project details"""
    client = ctx.obj['client']

    try:
        project = client.get_project(project_id)

        console.print(f"\n[bold]{project['name']}[/bold]")
        console.print(f"[yellow]ID:[/yellow] {project['id']}")
        console.print(f"[yellow]Status:[/yellow] {project['status']}")
        console.print(f"[yellow]Description:[/yellow] {project['description']}")

        if project.get('github_repo_url'):
            console.print(f"[yellow]GitHub:[/yellow] {project['github_repo_url']}")

        console.print(f"[yellow]Created:[/yellow] {project['created_at']}")
        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.argument('project_id')
@click.pass_context
def plan(ctx, project_id):
    """Show complete project plan"""
    client = ctx.obj['client']

    try:
        plan = client.get_project_plan(project_id)

        project = plan['project']
        console.print(f"\n[bold]{project['name']}[/bold]")
        console.print(f"{project['description']}\n")

        for epic in plan['epics']:
            console.print(f"\n[bold cyan]Epic: {epic['title']}[/bold cyan]")
            console.print(f"  Priority: {epic['priority']} | Status: {epic['status']}")

            for story in epic['stories']:
                console.print(f"\n  [bold]Story: {story['title']}[/bold]")
                if story.get('story_points'):
                    console.print(f"    Points: {story['story_points']}")

                console.print("    [dim]Tasks:[/dim]")
                for task in story['tasks']:
                    status_icon = {
                        'todo': '⭕',
                        'in_progress': '🔄',
                        'done': '✅',
                        'blocked': '🚫'
                    }.get(task['status'], '⭕')

                    console.print(f"      {status_icon} [{task['task_type']}] {task['title']}")

        console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.option('--status', help='Filter by status')
@click.pass_context
def list(ctx, status):
    """List all projects"""
    client = ctx.obj['client']

    try:
        result = client.list_projects(status)

        table = Table(title="Projects")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bold")
        table.add_column("Status", style="yellow")
        table.add_column("Updated", style="dim")

        for project in result['projects']:
            table.add_row(
                project['id'][:8] + "...",
                project['name'],
                project['status'],
                project['updated_at'][:10]
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


@cli.command()
@click.argument('project_id')
@click.option('--limit', default=5, help='Number of tasks to show')
@click.pass_context
def tasks(ctx, project_id, limit):
    """Show next tasks to work on"""
    client = ctx.obj['client']

    try:
        result = client.get_next_tasks(project_id, limit)

        console.print(f"\n[bold]Next {limit} Tasks[/bold]\n")

        for i, task in enumerate(result['next_tasks'], 1):
            console.print(f"{i}. [bold]{task['title']}[/bold]")
            console.print(f"   Type: {task['task_type']}")
            console.print(f"   Epic: {task['epic']} → Story: {task['story']}")
            if task.get('estimated_hours'):
                console.print(f"   Estimated: {task['estimated_hours']}h")
            console.print()

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")


if __name__ == "__main__":
    cli(obj={})
