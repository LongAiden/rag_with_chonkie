# Docker Setup Summary 🐳

Complete Docker containerization for cross-platform deployment (macOS + Windows).

---

## 📦 What Was Created

### 1. **Docker Configuration Files**

| File | Purpose |
|------|---------|
| [Dockerfile](Dockerfile) | Main application container (Python 3.11 + FastAPI) |
| [deployment/Dockerfile.postgres](deployment/Dockerfile.postgres) | PostgreSQL 16 + pgvector + pgRouting + PostGIS |
| [docker-compose.yml](docker-compose.yml) | Production/main orchestration |
| [docker-compose.dev.yml](docker-compose.dev.yml) | Development overrides (hot reload, debug) |
| [.dockerignore](.dockerignore) | Files to exclude from Docker build |

### 2. **Documentation**

| File | Purpose |
|------|---------|
| [DOCKER_SETUP_GUIDE.md](DOCKER_SETUP_GUIDE.md) | **Complete installation guide** for Mac & Windows |
| [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) | **Quick start guide** (5 minutes to running) |
| [DOCKER_SUMMARY.md](DOCKER_SUMMARY.md) | This file - overview of Docker setup |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│              Docker Compose Network                   │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────────┐        ┌──────────────────┐    │
│  │   rag_app       │  <───> │  rag_postgres    │    │
│  │                 │        │                  │    │
│  │ FastAPI Server  │        │ PostgreSQL 16    │    │
│  │ Port: 8000      │        │ Port: 5432       │    │
│  │                 │        │                  │    │
│  │ • REST API      │        │ ✓ pgvector       │    │
│  │ • Entity Ext.   │        │ ✓ pgRouting      │    │
│  │ • Graph Service │        │ ✓ PostGIS        │    │
│  │ • Hot Reload    │        │ ✓ Auto-migrations│    │
│  └─────────────────┘        └──────────────────┘    │
│         │                            │               │
│    Code Volume                  Data Volume          │
│   (Live Editing)              (Persistent)           │
│                                                       │
│  ┌─────────────────┐                                 │
│  │   pgadmin       │  (Optional - Dev Mode)          │
│  │   Port: 5050    │                                 │
│  └─────────────────┘                                 │
│                                                       │
└──────────────────────────────────────────────────────┘
         ↓                              ↓
   Exposed Ports                Docker Volumes
   • 8000 (API)                 • postgres_data
   • 5432 (DB)                  • upload_data
   • 5050 (pgAdmin)             • pgadmin_data
```

---

## 🚀 Quick Start Commands

### First Time Setup

```bash
# 1. Setup environment
cp deployment/.env.example deployment/.env
# Edit .env and add GOOGLE_API_KEY

# 2. Build and start
docker-compose up --build

# 3. Test
curl http://localhost:8000/health
```

### Development Mode (Hot Reload)

```bash
# Start with development config
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Includes:
# - Hot reload on code changes
# - Debug logging
# - pgAdmin UI
```

### Production Mode

```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## 🎯 Services Included

### 1. **Application Container** (rag_app)

**Base Image**: Python 3.11-slim

**Includes**:
- FastAPI server
- All Python dependencies
- Entity extraction (Gemini)
- Graph service (pgRouting client)
- Vector embeddings (SentenceTransformers)

**Features**:
- ✅ Hot reload (development)
- ✅ Health checks
- ✅ Auto-restart
- ✅ Volume mounting for uploads
- ✅ Log persistence

**Ports**: 8000 (API)

### 2. **Database Container** (rag_postgres)

**Base Image**: PostgreSQL 16

**Extensions**:
- ✅ **pgvector** v0.7.4 - Vector similarity search
- ✅ **pgRouting** - Graph algorithms (Dijkstra, PageRank, etc.)
- ✅ **PostGIS** 3 - Spatial database (required by pgRouting)
- ✅ **uuid-ossp** - UUID generation

**Features**:
- ✅ Auto-run migrations on first start
- ✅ Persistent data storage
- ✅ Health checks
- ✅ Performance tuning
- ✅ Connection pooling

**Ports**: 5432 (PostgreSQL)

### 3. **pgAdmin** (rag_pgadmin) - Optional

**Base Image**: dpage/pgadmin4:latest

**Features**:
- ✅ Web-based database management
- ✅ Query editor
- ✅ Schema visualization
- ✅ Only runs with `--profile dev`

**Ports**: 5050 (Web UI)

---

## 📁 File Structure

```
rag_llama_index/
├── Dockerfile                      # App container definition
├── docker-compose.yml              # Main orchestration
├── docker-compose.dev.yml          # Dev overrides
├── .dockerignore                   # Build exclusions
│
├── deployment/
│   ├── Dockerfile.postgres         # DB container with extensions
│   ├── .env                        # Environment variables
│   └── .env.example                # Template
│
├── migrations/
│   └── 001_create_graph_tables.sql # Auto-run on DB init
│
├── DOCKER_SETUP_GUIDE.md           # Full installation guide
├── DOCKER_QUICKSTART.md            # Quick start (5 min)
└── DOCKER_SUMMARY.md               # This file
```

---

## 🔧 Key Features

### 1. **Cross-Platform Compatibility**
- ✅ Works on macOS (Intel & Apple Silicon)
- ✅ Works on Windows (WSL 2)
- ✅ Works on Linux
- ✅ No platform-specific setup needed

### 2. **Development-Friendly**
- ✅ **Hot reload**: Code changes reflect instantly
- ✅ **Volume mounting**: Edit files locally
- ✅ **Debug logging**: See everything that's happening
- ✅ **pgAdmin**: Visual database management

### 3. **Production-Ready**
- ✅ **Health checks**: Automatic service monitoring
- ✅ **Auto-restart**: Services restart on failure
- ✅ **Persistent storage**: Data survives container restarts
- ✅ **Optimized images**: Minimal size, fast startup
- ✅ **Logging**: Centralized log collection

### 4. **Database Excellence**
- ✅ **All extensions pre-installed**: pgvector, pgRouting, PostGIS
- ✅ **Automatic migrations**: Run on first startup
- ✅ **Performance tuned**: Optimized PostgreSQL config
- ✅ **Health monitoring**: Connection checks

### 5. **Easy Management**
- ✅ **One command start**: `docker-compose up`
- ✅ **One command stop**: `docker-compose down`
- ✅ **Easy logs**: `docker-compose logs -f`
- ✅ **Easy rebuild**: `docker-compose up --build`

---

## 🌍 Environment Variables

All configurable via `.env` file:

### Database
```bash
POSTGRES_DB=rag_db
POSTGRES_USER=admin
POSTGRES_PASSWORD=admin
```

### API Keys
```bash
GOOGLE_API_KEY=your-api-key          # Required
LOGFIRE_WRITE_TOKEN=optional
LOGFIRE_READ_TOKEN=optional
```

### Graph Configuration
```bash
ENTITY_CONFIDENCE_THRESHOLD=0.6
RELATIONSHIP_CONFIDENCE_THRESHOLD=0.6
MAX_ENTITIES_PER_CHUNK=50
MAX_RELATIONSHIPS_PER_CHUNK=100
DEFAULT_MAX_HOPS=2
GEMINI_MODEL=gemini-2.0-flash-exp
```

### Performance
```bash
BATCH_SIZE=10
ENABLE_PARALLEL_EXTRACTION=true
ENABLE_ENTITY_CACHING=true
CACHE_TTL_SECONDS=3600
LOG_LEVEL=INFO
```

See [deployment/.env.example](deployment/.env.example) for all options.

---

## 📊 Docker Commands Reference

### Service Management
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Start with rebuild
docker-compose up --build

# Start dev mode (with pgAdmin)
docker-compose --profile dev up

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ deletes data)
docker-compose down -v
```

### Logs & Monitoring
```bash
# All logs (follow)
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100

# Check status
docker-compose ps
```

### Container Access
```bash
# App container shell
docker-compose exec app bash

# PostgreSQL shell
docker-compose exec postgres psql -U admin -d rag_db

# Run Python script
docker-compose exec app python script.py

# Check extensions
docker-compose exec postgres psql -U admin -d rag_db -c "\dx"
```

### Database Operations
```bash
# Backup database
docker-compose exec postgres pg_dump -U admin rag_db > backup.sql

# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U admin -d rag_db

# Run migration
docker-compose exec postgres psql -U admin -d rag_db -f /path/to/migration.sql
```

---

## 🔍 Health Checks

All services include health checks:

### Application
```bash
# HTTP health check every 30s
curl http://localhost:8000/health

# Graph health check
curl http://localhost:8000/graph/health
```

### Database
```bash
# PostgreSQL ready check every 10s
docker-compose exec postgres pg_isready -U admin
```

### Status Check
```bash
docker-compose ps

# Should show:
# NAME           STATUS
# rag_postgres   Up (healthy)
# rag_app        Up (healthy)
```

---

## 📚 Data Persistence

Data is stored in Docker volumes:

| Volume | Purpose | Data |
|--------|---------|------|
| `postgres_data` | Database storage | Tables, indexes, embeddings |
| `upload_data` | File uploads | PDFs, documents |
| `pgadmin_data` | pgAdmin config | Saved connections, queries |

**Volumes persist** across container restarts and rebuilds.

**To delete volumes** (⚠️ WARNING):
```bash
docker-compose down -v  # Deletes ALL data
```

---

## 🚨 Troubleshooting

### Port Conflicts
```bash
# Change ports in docker-compose.yml
ports:
  - "8001:8000"  # Changed from 8000:8000
  - "5433:5432"  # Changed from 5432:5432
```

### Container Won't Start
```bash
# Check logs
docker-compose logs app

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

### Database Connection Issues
```bash
# Wait for database to be ready
docker-compose logs postgres | grep "ready"

# Check health
docker-compose ps

# Manual connection test
docker-compose exec postgres pg_isready -U admin
```

### Permission Errors (Linux)
```bash
# Fix ownership
sudo chown -R $USER:$USER .

# Or add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

---

## 📖 Documentation Map

**Start here**: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) (5 minutes)

**Installation**: [DOCKER_SETUP_GUIDE.md](DOCKER_SETUP_GUIDE.md) (Mac/Windows)

**Application Setup**:
- [GRAPH_INTEGRATION_GUIDE.md](GRAPH_INTEGRATION_GUIDE.md) - Graph features
- [ENTITY_CONFIG_REFERENCE.md](ENTITY_CONFIG_REFERENCE.md) - Configuration
- [GRAPH_SETUP_SUMMARY.md](GRAPH_SETUP_SUMMARY.md) - What's included

**API Documentation**: http://localhost:8000/docs (when running)

---

## ✅ Checklist

Before deploying:

**Development**
- [ ] Docker Desktop installed
- [ ] `.env` file created with `GOOGLE_API_KEY`
- [ ] Services start: `docker-compose up --build`
- [ ] Health check passes: `curl http://localhost:8000/health`
- [ ] Can upload document via API
- [ ] Hot reload works (edit code, see changes)

**Production**
- [ ] Strong passwords in `.env`
- [ ] `LOG_LEVEL=WARNING` or `ERROR`
- [ ] Remove code volume mount
- [ ] Set up SSL/TLS
- [ ] Configure backups
- [ ] Set up monitoring

---

## 🎉 Summary

You now have:

✅ **Complete Docker setup** for cross-platform deployment
✅ **PostgreSQL** with pgvector + pgRouting + PostGIS
✅ **FastAPI app** with hot reload and health checks
✅ **pgAdmin** for database management (dev mode)
✅ **Automatic migrations** on startup
✅ **Persistent data storage**
✅ **Comprehensive documentation**

**Run it**:
```bash
docker-compose up --build
```

**Access it**:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- pgAdmin: http://localhost:5050 (dev mode)

---

**Ready to deploy on any platform! 🚀**
