# Production Deployment Guide

This guide covers deploying the Project Manager MCP system using Docker and Docker Compose for production environments.

## Quick Start

```bash
# 1. Build and start the system
docker-compose up -d

# 2. Verify deployment
curl http://localhost:8080/healthz

# 3. Check logs
docker-compose logs -f

# 4. Stop the system
docker-compose down
```

## Architecture Overview

The deployment consists of:

- **Multi-stage Docker build** for optimized production images
- **Docker Compose orchestration** for complete system management
- **Persistent data volumes** for database and logs
- **Health checks** for container and load balancer monitoring
- **Security hardening** with non-root user and resource limits

## Configuration

### Environment Variables

Key production settings in `deploy/production.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `/app/data/tasks.db` | SQLite database file location |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `DEFAULT_PORT` | `8080` | Main API server port |
| `MCP_PORT` | `8081` | MCP Server-Sent Events port |
| `MCP_TRANSPORT` | `sse` | MCP transport protocol |
| `WEBSOCKET_MAX_CONNECTIONS` | `100` | Maximum WebSocket connections |
| `LOCK_CLEANUP_INTERVAL` | `300` | Lock cleanup interval in seconds |

### Port Mappings

- **8080**: Main API and dashboard interface
- **8081**: MCP Server-Sent Events endpoint

### Volume Mounts

- `project_data:/app/data` - Persistent database and logs
- `./examples:/app/examples:ro` - Read-only example files

## Security Features

### Container Security

- **Non-root user**: Application runs as `appuser` (uid 1000)
- **Read-only filesystem**: Examples mounted read-only
- **Security options**: `no-new-privileges` enabled
- **Resource limits**: CPU and memory constraints

### Network Security

- **CORS configuration**: Configurable origin restrictions
- **Service isolation**: Dedicated Docker network
- **Port exposure**: Only required ports exposed

## Health Monitoring

### Health Check Endpoints

#### `/healthz` - Load Balancer Health Check
```json
{
  "status": "healthy",
  "database_connected": true,
  "active_websocket_connections": 5,
  "timestamp": "2025-09-07T15:30:00Z"
}
```

#### `/api/metrics` - Operational Metrics
```json
{
  "connections": {"active": 12, "total_opened": 145},
  "tasks": {"total": 50, "locked": 3, "completed_today": 23},
  "performance": {"avg_query_time_ms": 2.1},
  "system": {"uptime_seconds": 3600, "memory_usage_mb": 45.2}
}
```

### Docker Health Checks

The container includes a comprehensive health check script that validates:

- **Port listening**: Service accepting connections
- **HTTP endpoints**: API responding correctly
- **Database file**: SQLite database accessible

```bash
# Check container health
docker-compose ps
docker inspect project-manager_project-manager_1 | grep -A 5 '"Health"'
```

## Performance Optimization

### Resource Configuration

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'        # Maximum CPU cores
      memory: 512M       # Maximum memory
    reservations:
      cpus: '0.5'        # Reserved CPU cores
      memory: 256M       # Reserved memory
```

### Database Optimization

- **WAL Mode**: Enabled for concurrent access
- **Connection pooling**: Configurable pool size
- **Lock cleanup**: Automatic expired lock removal
- **Query timeout**: Prevents long-running queries

## Scaling and High Availability

### Load Balancer Configuration

Use the `/healthz` endpoint for health checks:

```nginx
upstream project_manager {
    server server1:8080;
    server server2:8080;
}

server {
    location /healthz {
        access_log off;
        proxy_pass http://project_manager;
        proxy_connect_timeout 2s;
        proxy_read_timeout 3s;
    }
    
    location / {
        proxy_pass http://project_manager;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Multiple Instance Deployment

For high availability, run multiple containers:

```bash
# Scale to 3 instances
docker-compose up -d --scale project-manager=3

# Use external load balancer to distribute traffic
# Ensure shared database volume for consistency
```

## Logging and Monitoring

### Log Configuration

- **Format**: Structured JSON for log aggregation
- **Rotation**: 10MB max file size, 5 files retained
- **Levels**: Configurable via `LOG_LEVEL` environment variable

### Log Collection

```bash
# View logs
docker-compose logs -f project-manager

# Follow specific container
docker logs -f container_id

# Export logs for analysis
docker-compose logs --no-color project-manager > app.log
```

### Monitoring Integration

#### Prometheus Metrics (Future Enhancement)

The `/api/metrics` endpoint provides structured data suitable for Prometheus scraping.

#### Log Aggregation

JSON log format supports ELK stack, Splunk, or similar log analysis systems.

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check build logs
docker-compose build --no-cache

# Check startup logs
docker-compose logs project-manager

# Verify environment file
cat deploy/production.env
```

#### Health Check Failures

```bash
# Run health check manually
docker exec container_id python /app/docker-healthcheck.py

# Check service connectivity
docker exec container_id curl -f http://localhost:8080/healthz

# Verify database file
docker exec container_id ls -la /app/data/
```

#### Performance Issues

```bash
# Check resource usage
docker stats

# Review database performance
curl http://localhost:8080/api/metrics

# Analyze logs for slow queries
docker-compose logs project-manager | grep -i slow
```

### Recovery Procedures

#### Database Corruption

```bash
# Stop container
docker-compose down

# Backup current database
cp data/tasks.db data/tasks.db.backup

# Restore from backup or reinitialize
# Start container
docker-compose up -d
```

#### Container Recovery

```bash
# Force recreate containers
docker-compose down
docker-compose up -d --force-recreate

# Rebuild if needed
docker-compose build --no-cache
docker-compose up -d
```

## Security Considerations

### Production Hardening

1. **Environment Variables**: Store sensitive config in secure key management
2. **Network Security**: Use internal networks for database communication
3. **Access Control**: Implement authentication/authorization as needed
4. **TLS Termination**: Use reverse proxy for HTTPS termination
5. **Security Updates**: Regular base image and dependency updates

### Monitoring Security

- Monitor failed health checks
- Track unusual connection patterns
- Alert on resource exhaustion
- Log and monitor API access patterns

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker exec container_id sqlite3 /app/data/tasks.db ".backup /app/data/backup.db"

# Copy backup out of container
docker cp container_id:/app/data/backup.db ./backup-$(date +%Y%m%d).db
```

### Full System Backup

```bash
# Backup persistent volumes
docker run --rm -v project_data:/source -v $(pwd):/backup \
  alpine tar czf /backup/project-data-backup.tar.gz -C /source .
```

## Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Log Level | DEBUG | INFO |
| CORS Origins | * | Specific domains |
| Resource Limits | None | Enforced |
| Health Checks | Optional | Required |
| Data Persistence | Local files | Volumes |
| Security | Relaxed | Hardened |

---

For additional support or questions, refer to the project documentation or create an issue in the project repository.