-- AI Project Orchestrator Database Schema

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'planning' CHECK (status IN ('planning', 'refining', 'ready', 'in_progress', 'completed', 'archived')),
    github_repo_url VARCHAR(500),
    github_repo_name VARCHAR(255),
    tech_stack JSONB,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Epics table
CREATE TABLE epics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'blocked')),
    order_index INTEGER,
    github_milestone_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Stories table
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    epic_id UUID REFERENCES epics(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    user_story TEXT,
    acceptance_criteria TEXT[],
    story_points INTEGER,
    priority INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'blocked')),
    order_index INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    task_type VARCHAR(50) CHECK (task_type IN ('setup', 'feature', 'bug', 'test', 'documentation', 'refactor', 'deployment')),
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    status VARCHAR(50) DEFAULT 'todo' CHECK (status IN ('todo', 'in_progress', 'review', 'done', 'blocked')),
    order_index INTEGER,
    technical_details JSONB,
    github_issue_number INTEGER,
    github_issue_url VARCHAR(500),
    assigned_to VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table (for tracking AI conversations)
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    phase VARCHAR(50) CHECK (phase IN ('creation', 'refinement', 'execution', 'clarification')),
    messages JSONB NOT NULL DEFAULT '[]',
    current_state VARCHAR(50) DEFAULT 'active',
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Execution logs table (track Claude Code execution)
CREATE TABLE execution_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    execution_type VARCHAR(50),
    command TEXT,
    output TEXT,
    status VARCHAR(50),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB
);

-- Create indexes for better query performance
CREATE INDEX idx_epics_project ON epics(project_id);
CREATE INDEX idx_epics_status ON epics(status);
CREATE INDEX idx_stories_epic ON stories(epic_id);
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_tasks_story ON tasks(story_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(task_type);
CREATE INDEX idx_conversations_project ON conversations(project_id);
CREATE INDEX idx_conversations_phase ON conversations(phase);
CREATE INDEX idx_execution_logs_task ON execution_logs(task_id);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_epics_updated_at BEFORE UPDATE ON epics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stories_updated_at BEFORE UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for testing (optional, can be removed)
-- INSERT INTO projects (name, description, status) VALUES
-- ('Sample Project', 'A sample project for testing', 'planning');

-- Create views for easier querying
CREATE VIEW project_summary AS
SELECT
    p.id,
    p.name,
    p.description,
    p.status,
    p.github_repo_url,
    COUNT(DISTINCT e.id) as epic_count,
    COUNT(DISTINCT s.id) as story_count,
    COUNT(DISTINCT t.id) as task_count,
    COUNT(DISTINCT CASE WHEN t.status = 'done' THEN t.id END) as completed_tasks,
    p.created_at,
    p.updated_at
FROM projects p
LEFT JOIN epics e ON e.project_id = p.id
LEFT JOIN stories s ON s.epic_id = e.id
LEFT JOIN tasks t ON t.story_id = s.id
GROUP BY p.id;

CREATE VIEW task_details AS
SELECT
    t.id as task_id,
    t.title as task_title,
    t.description as task_description,
    t.status as task_status,
    t.task_type,
    t.estimated_hours,
    t.github_issue_url,
    s.id as story_id,
    s.title as story_title,
    e.id as epic_id,
    e.title as epic_title,
    p.id as project_id,
    p.name as project_name
FROM tasks t
JOIN stories s ON t.story_id = s.id
JOIN epics e ON s.epic_id = e.id
JOIN projects p ON e.project_id = p.id;

COMMENT ON TABLE projects IS 'Main projects table tracking all AI-orchestrated projects';
COMMENT ON TABLE epics IS 'High-level feature groupings within a project';
COMMENT ON TABLE stories IS 'User stories that break down epics into implementable units';
COMMENT ON TABLE tasks IS 'Individual technical tasks that implement stories';
COMMENT ON TABLE conversations IS 'AI conversation history for project planning and refinement';
COMMENT ON TABLE execution_logs IS 'Logs of Claude Code execution for tasks';
