# Edict Agent Architecture Redesign Document

## 1. Design Goals
- **Observability**: Dashboard can display each agent's thought stream (thoughts) and todo changes in real time.
- **Replayability & Audit**: All events and state changes are persisted and traceable.
- **Controllable Flow**: Retains Three Departments & Six Ministries logic, event-driven, supports human intervention.
- **Real-time & Scalable**: Low-latency interactions, supports horizontal scaling.
- **Structured Tasks & Pluggable Skills**: Todos and thoughts are structured, easy to render in UI and reuse.

## 2. Overall Components
1. **API Gateway / Control Plane** (REST + WebSocket)
2. **Orchestrator (Scheduling Core)**
3. **Event Bus / Stream Layer** (Redis Streams / NATS / Kafka)
4. **Agent Runtime Pool**
5. **Model / LLM Pool**
6. **Task Store / Audit DB** (Postgres + JSONB)
7. **Realtime Dashboard** (WebSocket client)
8. **Observability / Tracing** (Prometheus + Grafana + OpenTelemetry)

## 3. Communication Patterns
- **Event-Driven**: All inter-agent communication goes through the Event Bus
- **Topic examples**: `task.created`, `task.planning`, `task.review.request`, `task.review.result`, `task.dispatch`, `agent.thoughts`, `agent.todo.update`, `task.status`, `heartbeat`
- **Event structure**:
```json
{
  "event_id": "uuid",
  "trace_id": "task-uuid",
  "timestamp": "2026-03-01T12:00:00Z",
  "topic": "agent.thoughts",
  "event_type": "thought.append",
  "producer": "planning-agent:v1",
  "payload": { ... },
  "meta": { "priority": "normal", "model": "gpt-5-thinking", "version": "1" }
}
```

## 4. Thoughts & Todo JSON Schema
**Thought**:
```json
{
  "thought_id": "uuid",
  "trace_id": "task-uuid",
  "agent": "planning",
  "step": 3,
  "type": "reasoning|query|action_intent|summary",
  "source": "llm|tool|human",
  "content": "text",
  "tokens": 123,
  "confidence": 0.86,
  "sensitive": false,
  "timestamp": "2026-03-01T12:00:01Z"
}
```
**Todo**:
```json
{
  "todo_id": "uuid",
  "trace_id": "task-uuid",
  "parent_id": null,
  "title": "Verify data source X",
  "description": "Fetch last 30 days of records from table X, check for missing values",
  "owner": "exec-dpt-1",
  "assignee_agent": "data-agent",
  "status": "open",
  "priority": "high",
  "estimated_cost": 0.5,
  "created_by": "planner",
  "created_at": "2026-03-01T12:01:00Z",
  "checkpoints": [ {"name":"fetch","status":"done"}, {"name":"validate","status":"pending"} ],
  "metadata": { "requires_human_approval": true }
}
```

## 5. Sequence Diagram (Mermaid)
```mermaid
sequenceDiagram
    participant U as User
    participant D as Dashboard
    participant G as Gateway
    participant E as Event Bus
    participant O as Orchestrator
    participant P as Planning Agent
    participant R as Review Agent
    participant X as Executor Agent
    participant M as Model Pool

    U->>D: Create Task
    D->>G: POST /tasks
    G->>E: publish task.created
    E->>O: task.created
    O->>E: publish task.planning.request
    E->>P: task.planning.request
    P->>M: LLM streaming call
    M-->>P: token stream
    loop streaming thoughts
        P->>E: agent.thought.append
        E->>G: forward to subscribers
        G->>D: WS push thought chunk
    end
    P->>E: task.planning.complete
    E->>O: planning.complete
    O->>E: task.review.request
    E->>R: review.request
    R->>E: task.review.result
    alt accepted
        O->>E: task.dispatch
        E->>X: dispatch subtasks
    else rejected
        O->>E: task.replan
    end
    X->>M: execution LLM/tool
    loop execution progress
        X->>E: agent.todo.update
        E->>G: forward
        G->>D: WS update Kanban
    end
    X->>E: task.completed
    E->>O: complete
    O->>E: task.closed
```

## 6. WebSocket Subscription & Message Examples
**Subscribe message**:
```json
{
  "type": "subscribe",
  "channels": ["task:task-123", "agent:planning-agent", "global"]
}
```
**Thought append (partial)**:
```json
{
  "event": "agent.thought.append",
  "data": {
    "thought_id": "th-1",
    "step": 3,
    "partial": true,
    "type": "reasoning",
    "content": "We should split the task into...",
    "tokens": 15
  }
}
```
**Todo update**:
```json
{
  "event": "agent.todo.update",
  "data": {
    "todo_id": "todo-1",
    "status": "in_progress",
    "progress": 0.45
  }
}
```

## 7. Human Intervention Example
```json
{
  "type": "command",
  "action": "pause_task",
  "trace_id": "task-123"
}
```
Publishes event:
```json
{
  "event": "task.status",
  "data": {"status": "paused", "reason": "User intervention"}
}
```

## 8. Replay
- Request: `GET /tasks/task-123/events`
- Returns an array of events that can be replayed step-by-step on the Dashboard timeline

## 9. Recommended Tech Stack
| Layer | Technology |
|----|------|
| Event Bus | Redis Streams |
| API | FastAPI |
| WS | FastAPI WebSocket |
| DB | Postgres |
| Agent Runtime | Python asyncio worker |
| Frontend | React + Zustand |

---
**Note**: This document is a downloadable reference architecture design, containing event specifications, WebSocket protocol, sequence diagrams, and JSON Schema, suitable for implementing real-time agent observability systems.
