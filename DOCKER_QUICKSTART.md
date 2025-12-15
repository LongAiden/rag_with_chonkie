# Docker Quick Start 🚀

Get your RAG + Knowledge Graph application running in **5 minutes** with Docker.

---

## Prerequisites

✅ Docker Desktop installed ([Installation Guide](DOCKER_SETUP_GUIDE.md))
✅ Docker Compose V2 enabled
✅ Google API Key for Gemini

---

## Quick Start (TL;DR)

```bash
# 1. Copy environment file
cp deployment/.env.example deployment/.env

# 2. Edit .env and add your API key
# Set: GOOGLE_API_KEY=your-actual-api-key

# 3. Start everything
docker-compose up --build

# 4. Test the API
curl http://localhost:8000/health
```

**Done!** 🎉

- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Database: localhost:5432

---

## Step-by-Step Guide

### Step 1: Configure Environment

```bash
# Copy the example environment file
cp deployment/.env.example deployment/.env

# Edit the file (use any text editor)
nano deployment/.env
# OR
code deployment/.env
# OR
notepad deployment/.env  # Windows
```

**Add your Google API key:**
```bash
GOOGLE_API_KEY=your-actual-api-key-here
```

### Step 2: Start Services

```bash
# Build and start all services
docker-compose up --build

# Or run in background (detached mode)
docker-compose up --build -d
```

**Wait for the startup** (about 30-60 seconds):
```
✓ postgres container created
✓ Database initialized
✓ Migrations applied
✓ App container created
✓ Dependencies installed
✓ Server started on http://0.0.0.0:8000
```

### Step 3: Verify Everything Works

```bash
# Check if services are running
docker-compose ps

# Expected output:
# NAME           STATUS        PORTS
# rag_postgres   Up (healthy)  5432
# rag_app        Up (healthy)  8000

# Test the API
curl http://localhost:8000/health

# Test graph functionality
curl http://localhost:8000/graph/health
```

### Step 4: Access the Application

**API Documentation (Interactive)**:
```
http://localhost:8000/docs
```

**Upload a Document**:
```bash
curl -X POST "http://localhost:8000/upload_document" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_document.pdf" \
  -F "collection_name=test"
```

**Search**:
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is BERT?",
    "collection_name": "test",
    "top_k": 5
  }'
```

---

## Common Commands

### Starting & Stopping

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services (keeps data)
docker-compose down

# Stop and remove all data (⚠️ WARNING: deletes everything)
docker-compose down -v
```

### Viewing Logs

```bash
# View all logs
docker-compose logs -f

# View app logs only
docker-compose logs -f app

# View database logs only
docker-compose logs -f postgres

# View last 100 lines
docker-compose logs --tail=100
```

### Rebuilding

```bash
# Rebuild and restart everything
docker-compose up --build

# Rebuild specific service
docker-compose up --build app

# Force rebuild (no cache)
docker-compose build --no-cache
docker-compose up
```

### Container Access

```bash
# Open shell in app container
docker-compose exec app bash

# Run Python in app container
docker-compose exec app python

# Access PostgreSQL
docker-compose exec postgres psql -U admin -d rag_db

# Check installed extensions
docker-compose exec postgres psql -U admin -d rag_db -c "SELECT * FROM pg_extension;"
```

---

## Optional Features

### pgAdmin (Database UI)

Start with pgAdmin for database management:

```bash
docker-compose --profile dev up -d
```

Access at: http://localhost:5050
- Email: `admin@rag.local`
- Password: `admin`

---

## Troubleshooting

### Port Already in Use

**Error**: `Bind for 0.0.0.0:5432 failed: port is already allocated`

**Solution**:
```bash
# Option 1: Stop local PostgreSQL
# macOS:
brew services stop postgresql

# Windows:
net stop postgresql-x64-14

# Linux:
sudo systemctl stop postgresql

# Option 2: Change port in docker-compose.yml
# Edit: "5432:5432" → "5433:5432"
```

### Can't Connect to Database

```bash
# Wait for database to be ready
docker-compose logs postgres | grep "ready to accept connections"

# Check health status
docker-compose ps

# Should show:
# rag_postgres   Up (healthy)
```

### API Not Responding

```bash
# Check logs for errors
docker-compose logs app

# Restart the service
docker-compose restart app

# Or rebuild
docker-compose up --build app
```

### Database Missing Tables

```bash
# Check if migrations ran
docker-compose logs postgres | grep "CREATE TABLE"

# Manually apply migrations
docker-compose exec postgres psql -U admin -d rag_db -f /docker-entrypoint-initdb.d/001_create_graph_tables.sql
```

### Docker Desktop Not Running

**macOS/Windows**:
1. Open Docker Desktop application
2. Wait for whale icon to stop animating
3. Try command again

### Permission Denied (Linux)

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, or:
newgrp docker

# Then run commands without sudo
docker-compose up
```

---

## Development Workflow

### Code Changes (Hot Reload)

1. **Edit code** in your local directory
2. **Save the file**
3. **Server automatically reloads** ✨

```bash
# Watch logs to see reloads
docker-compose logs -f app

# You'll see:
# INFO:     Detected file change in '...'
# INFO:     Reloading...
```

### Adding New Python Packages

1. **Add to `deployment/requirements.txt`**:
   ```
   new-package>=1.0.0
   ```

2. **Rebuild the container**:
   ```bash
   docker-compose up --build app
   ```

### Database Migrations

1. **Create migration file** in `migrations/`
2. **Restart database** to apply:
   ```bash
   docker-compose restart postgres
   ```

---

## Data Persistence

Your data is stored in Docker volumes:

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect rag_llama_index_postgres_data

# Backup database
docker-compose exec postgres pg_dump -U admin rag_db > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U admin -d rag_db
```

---

## Production Checklist

Before deploying to production:

- [ ] Change default passwords in `.env`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Use production-ready `GEMINI_API_KEY`
- [ ] Set `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Remove dev volumes (code mounting)
- [ ] Use `--workers 4` for uvicorn
- [ ] Set up SSL/TLS
- [ ] Enable firewall rules
- [ ] Set up regular database backups
- [ ] Monitor logs and metrics

---

## Helpful Links

- 📘 [Full Installation Guide](DOCKER_SETUP_GUIDE.md) - Detailed setup for Mac/Windows
- 📘 [Graph Integration Guide](GRAPH_INTEGRATION_GUIDE.md) - Using knowledge graph features
- 📘 [Entity Config Reference](ENTITY_CONFIG_REFERENCE.md) - Configuration options
- 🐳 [Docker Documentation](https://docs.docker.com/)
- 🐘 [PostgreSQL Docs](https://www.postgresql.org/docs/)

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Docker Compose Network          │
├─────────────────────────────────────────┤
│                                         │
│  ┌───────────────┐  ┌───────────────┐  │
│  │  rag_app      │  │ rag_postgres  │  │
│  │  (FastAPI)    │←→│ (PostgreSQL)  │  │
│  │  Port: 8000   │  │ Port: 5432    │  │
│  │               │  │               │  │
│  │ • REST API    │  │ • pgvector    │  │
│  │ • Entity Ext. │  │ • pgRouting   │  │
│  │ • Graph Ops   │  │ • PostGIS     │  │
│  └───────────────┘  └───────────────┘  │
│         ↑                   ↑           │
│         │                   │           │
│    Volume Mount        Persistent      │
│    (Hot Reload)          Volume        │
│                                         │
│  ┌───────────────┐ (optional)          │
│  │  pgadmin      │                     │
│  │  Port: 5050   │                     │
│  └───────────────┘                     │
└─────────────────────────────────────────┘
         ↓              ↓
    Host Ports    Docker Volumes
    8000, 5432    postgres_data
    5050          upload_data
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | rag_db | Database name |
| `POSTGRES_USER` | admin | Database user |
| `POSTGRES_PASSWORD` | admin | Database password |
| `GOOGLE_API_KEY` | - | Gemini API key (required) |
| `ENTITY_CONFIDENCE_THRESHOLD` | 0.6 | Entity extraction threshold |
| `RELATIONSHIP_CONFIDENCE_THRESHOLD` | 0.6 | Relationship threshold |
| `MAX_ENTITIES_PER_CHUNK` | 50 | Max entities per chunk |
| `DEFAULT_MAX_HOPS` | 2 | Max hops for graph queries |
| `LOG_LEVEL` | INFO | Logging level |

See [.env.example](deployment/.env.example) for all options.

---

## Need Help?

1. **Check logs**: `docker-compose logs -f`
2. **Verify status**: `docker-compose ps`
3. **Test health**: `curl http://localhost:8000/health`
4. **Restart**: `docker-compose restart`
5. **Clean rebuild**: `docker-compose down -v && docker-compose up --build`
6. **Read full guide**: [DOCKER_SETUP_GUIDE.md](DOCKER_SETUP_GUIDE.md)

---

**Happy Coding! 🚀**
