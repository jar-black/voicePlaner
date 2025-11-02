"""
Claude API service for AI interactions
"""

import anthropic
from typing import List, Dict, Any
import json


class ClaudeService:
    """Service for interacting with Claude API"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    async def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 1.0
    ) -> str:
        """
        Send a chat request to Claude

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            system_prompt: System prompt to guide Claude's behavior
            max_tokens: Maximum tokens in response
            temperature: Temperature for response generation

        Returns:
            Claude's response text
        """
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages
        )

        return response.content[0].text

    async def analyze_project_description(self, description: str) -> Dict[str, Any]:
        """
        Analyze initial project description and extract structured information

        Args:
            description: Initial project description from user

        Returns:
            Structured analysis of the project
        """
        system_prompt = """You are a software project analyst. Analyze the user's project description and extract key information.

Respond with a JSON object containing:
- project_name: A concise name for the project
- project_type: The type of project (web_app, mobile_app, api, library, etc.)
- tech_stack: Suggested technology stack
- complexity: Estimated complexity (simple, moderate, complex)
- clarification_questions: List of questions to ask the user for clarification
- initial_epics: Suggested high-level features/epics

Be concise and practical."""

        messages = [
            {"role": "user", "content": f"Analyze this project description:\n\n{description}"}
        ]

        response = await self.chat(messages, system_prompt)

        # Try to extract JSON from response
        try:
            # Look for JSON in code blocks or raw
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response

            return json.loads(json_str)
        except Exception as e:
            # If JSON parsing fails, return a basic structure
            return {
                "project_name": "Untitled Project",
                "project_type": "unknown",
                "tech_stack": {},
                "complexity": "moderate",
                "clarification_questions": ["Could you provide more details about the project?"],
                "initial_epics": [],
                "raw_response": response
            }

    async def refine_project_plan(
        self,
        conversation_history: List[Dict[str, str]],
        user_message: str
    ) -> Dict[str, Any]:
        """
        Continue refining the project plan based on conversation

        Args:
            conversation_history: Previous messages in the conversation
            user_message: New message from user

        Returns:
            Response with refined plan or more questions
        """
        system_prompt = """You are a software project planning assistant helping to refine a project plan.

Your goal is to:
1. Understand the user's requirements thoroughly
2. Ask clarifying questions about unclear aspects
3. Help define the project structure (epics, stories, tasks)
4. Once you have enough information, indicate that the project is ready to finalize

When you have enough information, structure your response as JSON with:
- ready_to_finalize: true/false
- project_structure: {epics: [{title, description, stories: [{title, description, tasks: [...]}]}]}
- remaining_questions: []

Otherwise, ask 2-3 focused questions to gather more information."""

        messages = conversation_history + [
            {"role": "user", "content": user_message}
        ]

        response = await self.chat(messages, system_prompt, max_tokens=8192)

        # Try to determine if plan is ready
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
                plan_data = json.loads(json_str)
                return {
                    "response": response,
                    "ready_to_finalize": plan_data.get("ready_to_finalize", False),
                    "plan_data": plan_data
                }
        except:
            pass

        return {
            "response": response,
            "ready_to_finalize": False,
            "plan_data": None
        }

    async def generate_project_structure(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generate final project structure from conversation history

        Args:
            conversation_history: Full conversation history

        Returns:
            Structured project plan with epics, stories, and tasks
        """
        system_prompt = """Based on the conversation history, generate a comprehensive project structure.

Create a JSON structure with:
{
  "project": {
    "name": "Project Name",
    "description": "Detailed description",
    "tech_stack": {...}
  },
  "epics": [
    {
      "title": "Epic Title",
      "description": "Epic Description",
      "priority": 1-10,
      "stories": [
        {
          "title": "Story Title",
          "description": "Story Description",
          "user_story": "As a... I want... So that...",
          "acceptance_criteria": ["criterion 1", "criterion 2"],
          "story_points": 1-13,
          "tasks": [
            {
              "title": "Task Title",
              "description": "Task Description",
              "task_type": "setup|feature|bug|test|documentation|refactor|deployment",
              "estimated_hours": number,
              "technical_details": {...}
            }
          ]
        }
      ]
    }
  ]
}

Be thorough and practical. Break down the project into implementable tasks."""

        messages = conversation_history + [
            {"role": "user", "content": "Please generate the complete project structure now."}
        ]

        response = await self.chat(messages, system_prompt, max_tokens=8192)

        # Extract JSON
        try:
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response

            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Failed to parse project structure: {str(e)}\n\nResponse: {response}")
