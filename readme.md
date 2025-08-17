# Self-Heal ITOps

Self-Heal ITOps is an AI-powered incident self-healing system designed to automatically detect, analyze, and resolve IT operational issues.  
It leverages agent-based architecture to reduce downtime, improve system reliability, and minimize manual intervention.

## Problem Statement
IT operations frequently face incidents such as service failures, misconfigurations, and system crashes.  
Traditional incident management is often:
- Time-consuming  
- Error-prone  
- Costly  

**Self-Heal ITOps** introduces a proactive and automated approach to incident detection, analysis, and resolution.

## Architecture

### Agents
- **Supervisor Agent** – Orchestrates workflows, opens and closes incidents, manages logs.  
- **Monitor Agent** – Detects system incidents and forwards them to the supervisor.  
- **Analyzer Agent** – Diagnoses incidents and suggests possible resolutions.  
- **Fixer Agent** – Executes recovery actions and confirms successful resolution.  

### Workflow
1. Monitor detects an incident.  
2. Supervisor logs and assigns the incident.  
3. Analyzer evaluates the incident and suggests a fix.  
4. Fixer applies the solution.  
5. Supervisor verifies resolution and closes the incident.  

## Tech Stack
- **Python 3.11+**  
- **FastAPI** – REST API framework  
- **Pydantic** – Data validation  
- **Asyncio** – Asynchronous orchestration  
- **JSONL** – Structured incident logging  

## API Usage

### Endpoint: Publish Event
```
POST /publish_event
```

#### Example Request
```json
{
  "type": "service_down",
  "source": "external",
  "payload": {
    "service": "database",
    "timestamp": "2025-08-18T12:34:56Z"
  }
}
```

#### Example Response
```json
{
  "status": "incident_opened",
  "incident_id": "12345",
  "message": "Incident logged and under analysis."
}
```

## Incident Logs
All incidents are logged in JSONL format at:
```
./data/incident_logs.jsonl
```

Each log contains:
- `incident_id`  
- `timestamp`  
- `incident_type`  
- `analysis`  
- `resolution`  


## Key Features
- Automated incident detection, analysis, and resolution  
- Modular agent-based design for flexibility  
- Structured logging for audit and review  
- Scalable for enterprise IT operations  

## Future Enhancements
- Integration with monitoring tools (Prometheus, Grafana)  
- Advanced anomaly detection using machine learning  
- Cloud deployment (AWS, GCP, Azure)  
- Integration with collaboration platforms (Slack, Teams)  

