# Docker Setup Guide for RAG + Knowledge Graph

This guide will help you install Docker and run the RAG application on **macOS** and **Windows**.

---

## 📦 What's Included

The Docker setup includes:
- **PostgreSQL 16** with pgvector, pgRouting, and PostGIS extensions
- **RAG Application** with FastAPI and all dependencies
- **pgAdmin** (optional) for database management
- **Automatic migrations** on first startup
- **Hot reload** for development
- **Persistent data** storage

---

## 🖥️ Part 1: Installing Docker

### **For macOS** 🍎

#### Option 1: Docker Desktop (Recommended)

1. **Download Docker Desktop**
   - Visit: https://www.docker.com/products/docker-desktop/
   - Click "Download for Mac"
   - Choose your chip:
     - **Apple Silicon (M1/M2/M3)**: Download "Mac with Apple chip"
     - **Intel**: Download "Mac with Intel chip"

2. **Install Docker Desktop**
   ```bash
   # Open the downloaded .dmg file
   # Drag Docker.app to Applications folder
   # Launch Docker from Applications
   ```

3. **Verify Installation**
   ```bash
   docker --version
   docker-compose --version

   # Expected output:
   # Docker version 24.x.x
   # Docker Compose version 2.x.x
   ```

#### Option 2: Homebrew (Alternative)

```bash
# Install Docker Desktop via Homebrew
brew install --cask docker

# Start Docker Desktop
open /Applications/Docker.app

# Verify
docker --version
```

#### Post-Installation (macOS)

1. **Allow Docker in System Preferences**
   - Go to System Preferences → Security & Privacy
   - Click "Open Anyway" if prompted

2. **Configure Resources (Recommended)**
   - Open Docker Desktop
   - Go to Preferences → Resources
   - Set:
     - **CPUs**: 4 (or half of your total)
     - **Memory**: 4 GB (minimum), 8 GB (recommended)
     - **Swap**: 1 GB
     - **Disk**: 50 GB

3. **Enable Docker Compose V2**
   - Docker Desktop → Preferences → General
   - Check "Use Docker Compose V2"

---

### **For Windows** 🪟

#### System Requirements

- **Windows 10/11 64-bit**: Pro, Enterprise, or Education (Build 19041 or higher)
- **OR Windows 10/11 Home** with WSL 2
- **Virtualization must be enabled** in BIOS

#### Step 1: Enable WSL 2 (Windows Subsystem for Linux)

1. **Open PowerShell as Administrator**
   ```powershell
   # Enable WSL
   wsl --install

   # Set WSL 2 as default
   wsl --set-default-version 2
   ```

2. **Restart your computer**

3. **Verify WSL 2**
   ```powershell
   wsl --list --verbose

   # Should show version 2
   ```

#### Step 2: Install Docker Desktop

1. **Download Docker Desktop**
   - Visit: https://www.docker.com/products/docker-desktop/
   - Click "Download for Windows"

2. **Run the Installer**
   - Double-click `Docker Desktop Installer.exe`
   - Check "Use WSL 2 instead of Hyper-V" (recommended)
   - Click "Ok" and follow the prompts

3. **Start Docker Desktop**
   - Search for "Docker Desktop" in Start Menu
   - Launch the application
   - Wait for Docker to start (whale icon in system tray)

4. **Verify Installation**
   ```powershell
   docker --version
   docker-compose --version

   # Expected output:
   # Docker version 24.x.x
   # Docker Compose version 2.x.x
   ```

#### Post-Installation (Windows)

1. **Configure Resources**
   - Open Docker Desktop
   - Go to Settings → Resources → WSL Integration
   - Enable integration with your WSL 2 distro (Ubuntu recommended)
   - Set:
     - **CPUs**: 4
     - **Memory**: 4-8 GB
     - **Swap**: 1 GB
     - **Disk**: 50 GB

2. **Enable File Sharing (if needed)**
   - Settings → Resources → File Sharing
   - Add your project directory

---

## 🚀 Part 2: Running the RAG Application

### Step 1: Clone/Navigate to Project

```bash
# Navigate to your project directory
cd /path/to/rag_llama_index

# Or on Windows:
cd C:\path\to\rag_llama_index
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env file with your settings
# REQUIRED: Set your Google API key
nano .env  # or use any text editor
```

**Minimum required in `.env`**:
```bash
GOOGLE_API_KEY=your-actual-api-key-here
```

### Step 3: Build and Start Services

```bash
# Build and start all services
docker-compose up --build

# Or run in detached mode (background)
docker-compose up --build -d

# View logs (if running in background)
docker-compose logs -f app
```

**What happens:**
1. PostgreSQL container builds with pgvector + pgRouting
2. Database migrations run automatically
3. Application container builds and starts
4. FastAPI server starts on http://localhost:8000

### Step 4: Verify Everything is Running

```bash
# Check running containers
docker-compose ps

# Expected output:
# NAME           STATUS        PORTS
# rag_postgres   Up (healthy)  5432
# rag_app        Up (healthy)  8000
```

**Test the API:**
```bash
# Health check
curl http://localhost:8000/health

# Graph health check
curl http://localhost:8000/graph/health

# API documentation
open http://localhost:8000/docs
```

---

## 🎯 Common Commands

### Start Services
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Start specific service
docker-compose up postgres
```

### Stop Services
```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
```

### Rebuild Services
```bash
# Rebuild everything
docker-compose up --build

# Rebuild specific service
docker-compose up --build app
```

### Execute Commands in Container
```bash
# Enter app container shell
docker-compose exec app bash

# Enter PostgreSQL shell
docker-compose exec postgres psql -U admin -d rag_db

# Run Python script
docker-compose exec app python script.py
```

### Database Commands
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U admin -d rag_db

# Run SQL file
docker-compose exec postgres psql -U admin -d rag_db -f /path/to/file.sql

# Check extensions
docker-compose exec postgres psql -U admin -d rag_db -c "SELECT * FROM pg_extension;"
```

---

## 🛠️ Development Workflow

### Hot Reload (Automatic Code Changes)

The application supports hot reload - code changes are automatically reflected without rebuilding:

1. **Edit your code** in the project directory
2. **Save the file**
3. **Server automatically reloads** (watch the logs)

```bash
# Watch logs to see reloads
docker-compose logs -f app
```

### Installing New Python Packages

1. **Add package to `requirements.txt`**
2. **Rebuild the container**:
   ```bash
   docker-compose up --build app
   ```

### Database Migrations

```bash
# Add new migration file to migrations/
# Restart database to apply
docker-compose restart postgres

# Or manually apply
docker-compose exec postgres psql -U admin -d rag_db -f /docker-entrypoint-initdb.d/002_new_migration.sql
```

---

## 🎨 Optional: pgAdmin (Database UI)

### Start pgAdmin
```bash
# Start with dev profile
docker-compose --profile dev up -d

# Access pgAdmin
open http://localhost:5050
```

### Login to pgAdmin
- **Email**: `admin@rag.local` (or set in .env)
- **Password**: `admin` (or set in .env)

### Connect to Database
1. Click "Add New Server"
2. **General Tab**:
   - Name: `RAG Database`
3. **Connection Tab**:
   - Host: `postgres` (container name)
   - Port: `5432`
   - Database: `rag_db`
   - Username: `admin`
   - Password: `admin`
4. Click "Save"

---

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Error: port 5432 already in use

# Option 1: Stop local PostgreSQL
# macOS:
brew services stop postgresql

# Windows:
net stop postgresql-x64-14

# Option 2: Change port in docker-compose.yml
# Change "5432:5432" to "5433:5432"
# Then connect to localhost:5433
```

### Container Fails to Start

```bash
# View detailed logs
docker-compose logs app
docker-compose logs postgres

# Restart specific service
docker-compose restart app

# Rebuild from scratch
docker-compose down -v
docker-compose up --build
```

### Permission Denied (Linux/macOS)

```bash
# Fix volume permissions
sudo chown -R $USER:$USER .

# Or run Docker commands with sudo
sudo docker-compose up
```

### Database Connection Refused

```bash
# Wait for PostgreSQL to be ready
docker-compose logs postgres

# Check health status
docker-compose ps

# Manually test connection
docker-compose exec postgres pg_isready -U admin
```

### WSL 2 Issues (Windows)

```bash
# Update WSL
wsl --update

# Restart WSL
wsl --shutdown

# Check WSL status
wsl --list --verbose
```

### Docker Desktop Not Starting (macOS)

```bash
# Reset Docker Desktop
# Open Docker Desktop → Troubleshoot → Reset to factory defaults

# Or reinstall
brew uninstall --cask docker
brew install --cask docker
```

---

## 📊 Performance Tips

### macOS
- Allocate at least 4 GB RAM to Docker
- Enable "Use gRPC FUSE for file sharing" (faster)
- Use Docker volumes instead of bind mounts for better performance

### Windows (WSL 2)
- Store project files in WSL filesystem (`\\wsl$\Ubuntu\home\...`)
- Not in Windows filesystem (`C:\Users\...`)
- Allocate sufficient RAM in `.wslconfig`:
  ```ini
  # %UserProfile%\.wslconfig
  [wsl2]
  memory=8GB
  processors=4
  ```

---

## 🔒 Production Deployment

For production, create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}  # Use strong password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # No port exposure (internal only)

  app:
    command: uvicorn document_processing.full_pipeline_pgvector:app --host 0.0.0.0 --port 8000 --workers 4
    environment:
      LOG_LEVEL: WARNING
    # Remove volume mount for code
```

Run with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 📚 Resources

### Docker Documentation
- **Official Docker Docs**: https://docs.docker.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **Best Practices**: https://docs.docker.com/develop/dev-best-practices/

### Platform-Specific
- **Docker Desktop for Mac**: https://docs.docker.com/desktop/mac/
- **Docker Desktop for Windows**: https://docs.docker.com/desktop/windows/
- **WSL 2 Backend**: https://docs.docker.com/desktop/windows/wsl/

### PostgreSQL + Extensions
- **pgvector**: https://github.com/pgvector/pgvector
- **pgRouting**: https://pgrouting.org/
- **PostGIS**: https://postgis.net/

---

## ✅ Quick Start Checklist

- [ ] Install Docker Desktop
- [ ] Verify: `docker --version` and `docker-compose --version`
- [ ] Clone/navigate to project directory
- [ ] Copy `.env.example` to `.env`
- [ ] Set `GOOGLE_API_KEY` in `.env`
- [ ] Run `docker-compose up --build`
- [ ] Test: `curl http://localhost:8000/health`
- [ ] Access API docs: http://localhost:8000/docs
- [ ] (Optional) Access pgAdmin: http://localhost:5050

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: `docker-compose logs -f`
2. **Verify health**: `docker-compose ps`
3. **Test connection**: `curl http://localhost:8000/health`
4. **Restart services**: `docker-compose restart`
5. **Clean rebuild**: `docker-compose down -v && docker-compose up --build`

---

**Happy Dockerizing! 🐳**
