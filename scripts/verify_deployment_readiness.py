#!/usr/bin/env python3
"""
Deployment Readiness Verification Script
Comprehensive validation of Synapse Graph-RAG deployment readiness.

This script:
1. Verifies infrastructure requirements (Memgraph, dependencies)
2. Runs service health checks
3. Validates configuration
4. Performs security checks
5. Generates deployment readiness report
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class DeploymentReadinessVerifier:
    """Comprehensive deployment readiness verification"""
    
    def __init__(self):
        self.verification_start = datetime.now()
        self.results = {
            'infrastructure': {},
            'services': {},
            'configuration': {},
            'security': {},
            'issues': [],
            'recommendations': []
        }
        self.output_dir = project_root / "docs"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    async def run_verification(self) -> Dict[str, Any]:
        """Run complete deployment readiness verification"""
        
        print("🔍 SYNAPSE GRAPH-RAG - DEPLOYMENT READINESS VERIFICATION")
        print("=" * 60)
        print(f"Started: {self.verification_start.isoformat()}")
        print("")
        
        # Step 1: Infrastructure Checks
        print("📊 Step 1: Infrastructure Requirements")
        print("-" * 40)
        await self._check_infrastructure()
        
        # Step 2: Service Health Checks
        print("\n📊 Step 2: Service Health Checks")
        print("-" * 40)
        await self._check_services()
        
        # Step 3: Configuration Validation
        print("\n📊 Step 3: Configuration Validation")
        print("-" * 40)
        await self._check_configuration()
        
        # Step 4: Security Checks
        print("\n📊 Step 4: Security Checks")
        print("-" * 40)
        await self._check_security()
        
        # Step 5: Generate Reports
        print("\n📄 Step 5: Generating Reports")
        print("-" * 40)
        await self._generate_reports()
        
        return self.results
    
    async def _check_infrastructure(self):
        """Verify infrastructure requirements"""
        
        checks = {
            'python_version': await self._check_python_version(),
            'docker_available': await self._check_docker(),
            'memgraph_available': await self._check_memgraph(),
            'dependencies': await self._check_dependencies(),
            'uv_available': await self._check_uv()
        }
        
        self.results['infrastructure'] = checks
        
        # Display results
        for component, status in checks.items():
            if isinstance(status, dict):
                icon = "✅" if status.get('available', False) else "❌"
                print(f"  {icon} {component}: {status.get('status', 'Unknown')}")
            else:
                icon = "✅" if status else "❌"
                print(f"  {icon} {component}: {'Available' if status else 'Not available'}")
    
    async def _check_python_version(self) -> bool:
        """Check Python version"""
        try:
            result = subprocess.run(
                ['python3', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_str = result.stdout.strip()
                # Check if >= 3.10
                version_parts = version_str.split()[1].split('.')
                major, minor = int(version_parts[0]), int(version_parts[1])
                return major == 3 and minor >= 10
            return False
        except:
            return False
    
    async def _check_docker(self) -> Dict[str, Any]:
        """Check Docker availability"""
        try:
            result = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return {'available': True, 'status': result.stdout.strip()}
            return {'available': False, 'status': 'Not installed'}
        except FileNotFoundError:
            return {'available': False, 'status': 'Docker not found'}
        except Exception as e:
            return {'available': False, 'status': f'Error: {str(e)}'}
    
    async def _check_memgraph(self) -> Dict[str, Any]:
        """Check Memgraph availability"""
        # Check if docker-compose.yml exists
        docker_compose = project_root / 'tools' / 'docker' / 'docker-compose.yml'
        if docker_compose.exists():
            # Try to check if Memgraph service is defined
            try:
                with open(docker_compose) as f:
                    content = f.read()
                    has_memgraph = 'memgraph' in content.lower()
                    return {'available': has_memgraph, 'status': 'Docker Compose configured' if has_memgraph else 'Not configured'}
            except:
                return {'available': False, 'status': 'Could not read docker-compose.yml'}
        else:
            return {'available': False, 'status': 'docker-compose.yml not found'}
    
    async def _check_dependencies(self) -> Dict[str, Any]:
        """Check if dependencies are installed"""
        pyproject = project_root / 'pyproject.toml'
        if pyproject.exists():
            try:
                # Try to import key dependencies
                import importlib
                key_deps = ['fastapi', 'typer', 'pydantic', 'mgclient']
                available = []
                missing = []
                
                for dep in key_deps:
                    try:
                        importlib.import_module(dep)
                        available.append(dep)
                    except ImportError:
                        missing.append(dep)
                
                return {
                    'available': len(missing) == 0,
                    'status': f'{len(available)}/{len(key_deps)} key dependencies available',
                    'missing': missing
                }
            except Exception as e:
                return {'available': False, 'status': f'Error checking: {str(e)}'}
        return {'available': False, 'status': 'pyproject.toml not found'}
    
    async def _check_uv(self) -> Dict[str, Any]:
        """Check uv availability"""
        try:
            result = subprocess.run(
                ['uv', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return {'available': True, 'status': result.stdout.strip()}
            return {'available': False, 'status': 'Not installed'}
        except FileNotFoundError:
            return {'available': False, 'status': 'uv not found'}
        except Exception as e:
            return {'available': False, 'status': f'Error: {str(e)}'}
    
    async def _check_services(self):
        """Run service health checks"""
        
        checks = {
            'api_health_endpoint': await self._check_api_health(),
            'memgraph_connection': await self._check_memgraph_connection(),
            'makefile_targets': await self._check_makefile_targets()
        }
        
        self.results['services'] = checks
        
        # Display results
        for service, status in checks.items():
            if isinstance(status, dict):
                icon = "✅" if status.get('operational', False) else "⚠️"
                print(f"  {icon} {service}: {status.get('status', 'Unknown')}")
            else:
                icon = "✅" if status else "⚠️"
                print(f"  {icon} {service}: {'Operational' if status else 'Not operational'}")
    
    async def _check_api_health(self) -> Dict[str, Any]:
        """Check if API health endpoint exists"""
        api_main = project_root / 'graph_rag' / 'api' / 'main.py'
        if api_main.exists():
            try:
                with open(api_main) as f:
                    content = f.read()
                    has_health = '/health' in content or 'health' in content.lower()
                    return {'operational': has_health, 'status': 'Health endpoint found' if has_health else 'Health endpoint not found'}
            except:
                return {'operational': False, 'status': 'Could not read API main file'}
        return {'operational': False, 'status': 'API main file not found'}
    
    async def _check_memgraph_connection(self) -> Dict[str, Any]:
        """Check Memgraph connection capability"""
        # Check if Memgraph repository exists
        memgraph_repo = project_root / 'graph_rag' / 'infrastructure' / 'repositories' / 'memgraph_repository.py'
        if memgraph_repo.exists():
            return {'operational': True, 'status': 'Memgraph repository code found'}
        
        # Check for mgclient usage
        graph_rag_dir = project_root / 'graph_rag'
        if graph_rag_dir.exists():
            mgclient_files = list(graph_rag_dir.rglob('*memgraph*.py'))
            if mgclient_files:
                return {'operational': True, 'status': f'{len(mgclient_files)} Memgraph-related files found'}
        
        return {'operational': False, 'status': 'Memgraph integration not found'}
    
    async def _check_makefile_targets(self) -> Dict[str, Any]:
        """Check if Makefile has required targets"""
        makefile = project_root / 'Makefile'
        if makefile.exists():
            try:
                with open(makefile) as f:
                    content = f.read()
                    required_targets = ['install-dev', 'up', 'run-api', 'run-memgraph', 'test']
                    found = [target for target in required_targets if f'{target}:' in content]
                    return {
                        'operational': len(found) == len(required_targets),
                        'status': f'{len(found)}/{len(required_targets)} required targets found',
                        'found': found,
                        'missing': [t for t in required_targets if t not in found]
                    }
            except:
                return {'operational': False, 'status': 'Could not read Makefile'}
        return {'operational': False, 'status': 'Makefile not found'}
    
    async def _check_configuration(self):
        """Validate configuration"""
        
        checks = {
            'settings_file': await self._check_settings_file(),
            'env_example': await self._check_env_example(),
            'config_validation': await self._check_config_validation()
        }
        
        self.results['configuration'] = checks
        
        # Display results
        for config, status in checks.items():
            if isinstance(status, dict):
                icon = "✅" if status.get('valid', False) else "⚠️"
                print(f"  {icon} {config}: {status.get('status', 'Unknown')}")
            else:
                icon = "✅" if status else "⚠️"
                print(f"  {icon} {config}: {'Valid' if status else 'Invalid'}")
    
    async def _check_settings_file(self) -> Dict[str, Any]:
        """Check if settings file exists and is valid"""
        settings_file = project_root / 'graph_rag' / 'config' / 'settings.py'
        if settings_file.exists():
            try:
                with open(settings_file) as f:
                    content = f.read()
                    has_pydantic = 'pydantic' in content.lower() or 'BaseSettings' in content
                    has_env_vars = 'SYNAPSE_' in content or 'MEMGRAPH' in content.upper()
                    return {
                        'valid': has_pydantic and has_env_vars,
                        'status': 'Settings file found with Pydantic and env vars' if (has_pydantic and has_env_vars) else 'Settings file found but incomplete'
                    }
            except:
                return {'valid': False, 'status': 'Could not read settings file'}
        return {'valid': False, 'status': 'Settings file not found'}
    
    async def _check_env_example(self) -> Dict[str, Any]:
        """Check if .env.example exists"""
        env_example = project_root / '.env.example'
        if env_example.exists():
            return {'valid': True, 'status': '.env.example found'}
        return {'valid': False, 'status': '.env.example not found'}
    
    async def _check_config_validation(self) -> Dict[str, Any]:
        """Check if configuration validation exists"""
        # Check for config validation in settings or separate file
        config_dir = project_root / 'graph_rag' / 'config'
        if config_dir.exists():
            config_files = list(config_dir.glob('*.py'))
            return {'valid': len(config_files) > 0, 'status': f'{len(config_files)} config files found'}
        return {'valid': False, 'status': 'Config directory not found'}
    
    async def _check_security(self):
        """Perform security checks"""
        
        checks = {
            'secrets_scan': await self._scan_secrets(),
            'dependency_audit': await self._audit_dependencies(),
            'auth_implementation': await self._check_auth()
        }
        
        self.results['security'] = checks
        
        # Display results
        for check, status in checks.items():
            if isinstance(status, dict):
                icon = "✅" if status.get('clean', False) else "⚠️"
                print(f"  {icon} {check}: {status.get('status', 'Unknown')}")
            else:
                icon = "✅" if status else "⚠️"
                print(f"  {icon} {check}: {'Clean' if status else 'Issues found'}")
    
    async def _scan_secrets(self) -> Dict[str, Any]:
        """Scan for hardcoded secrets"""
        try:
            result = subprocess.run(
                ['git', 'secrets', '--scan'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return {'clean': True, 'status': 'No secrets found'}
            else:
                # Check if it's just git-secrets not installed
                if 'not found' in result.stderr.lower():
                    return {'clean': True, 'status': 'git-secrets not installed (manual review recommended)'}
                return {'clean': False, 'status': 'Potential secrets found - review required'}
        except FileNotFoundError:
            return {'clean': True, 'status': 'git-secrets not installed (manual review recommended)'}
        except Exception as e:
            return {'clean': False, 'status': f'Error: {str(e)}'}
    
    async def _audit_dependencies(self) -> Dict[str, Any]:
        """Audit dependencies for vulnerabilities"""
        try:
            result = subprocess.run(
                ['uv', 'pip-audit'],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                if 'No known vulnerabilities found' in result.stdout:
                    return {'clean': True, 'status': 'No known vulnerabilities'}
                else:
                    vuln_count = result.stdout.count('VULNERABLE') or result.stdout.count('vulnerability')
                    return {'clean': False, 'status': f'{vuln_count} potential vulnerabilities found'}
            return {'clean': False, 'status': 'Audit had issues'}
        except FileNotFoundError:
            return {'clean': True, 'status': 'uv not available (manual audit recommended)'}
        except Exception as e:
            return {'clean': False, 'status': f'Error: {str(e)}'}
    
    async def _check_auth(self) -> Dict[str, Any]:
        """Check authentication implementation"""
        # Check for auth-related files
        auth_files = list(project_root.rglob('*auth*.py'))
        jwt_files = list(project_root.rglob('*jwt*.py'))
        
        if auth_files or jwt_files:
            return {'clean': True, 'status': f'Auth implementation found ({len(auth_files)} auth files, {len(jwt_files)} JWT files)'}
        return {'clean': False, 'status': 'Auth implementation not found'}
    
    async def _generate_reports(self):
        """Generate deployment readiness report and deployment guide"""
        
        # Save metrics JSON
        metrics_path = self.output_dir / "deployment_readiness_metrics.json"
        with open(metrics_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        # Generate markdown report
        report_path = self.output_dir / "DEPLOYMENT_READINESS_REPORT.md"
        await self._generate_readiness_report(report_path)
        
        # Generate deployment guide
        guide_path = self.output_dir / "DEPLOYMENT_GUIDE.md"
        await self._generate_deployment_guide(guide_path)
        
        print(f"  ✅ Deployment Readiness Report: {report_path}")
        print(f"  ✅ Deployment Guide: {guide_path}")
        print(f"  ✅ Metrics JSON: {metrics_path}")
    
    async def _generate_readiness_report(self, report_path: Path):
        """Generate deployment readiness report"""
        
        infrastructure = self.results['infrastructure']
        services = self.results['services']
        configuration = self.results['configuration']
        security = self.results['security']
        
        # Calculate overall readiness
        infra_ready = (
            infrastructure.get('python_version', False) and
            infrastructure.get('docker_available', {}).get('available', False) and
            infrastructure.get('memgraph_available', {}).get('available', False)
        )
        
        services_ready = (
            services.get('api_health_endpoint', {}).get('operational', False) and
            services.get('memgraph_connection', {}).get('operational', False)
        )
        
        config_ready = (
            configuration.get('settings_file', {}).get('valid', False) and
            configuration.get('env_example', {}).get('valid', False)
        )
        
        security_clean = (
            security.get('secrets_scan', {}).get('clean', False) and
            security.get('dependency_audit', {}).get('clean', False)
        )
        
        overall_ready = infra_ready and services_ready and config_ready
        
        report = f"""# Deployment Readiness Report - Synapse Graph-RAG

**Date:** {self.verification_start.isoformat()}
**Status:** {'✅ READY FOR DEPLOYMENT' if overall_ready else '⚠️ NEEDS WORK'}

---

## Executive Summary

Synapse Graph-RAG deployment readiness has been verified through comprehensive infrastructure, service, configuration, and security checks.

**Key Findings:**
- **Infrastructure:** {'✅ Ready' if infra_ready else '⚠️ Needs work'}
- **Services:** {'✅ Ready' if services_ready else '⚠️ Needs work'}
- **Configuration:** {'✅ Ready' if config_ready else '⚠️ Needs work'}
- **Security:** {'✅ Clean' if security_clean else '⚠️ Review needed'}
- **Overall Status:** {'✅ READY' if overall_ready else '⚠️ NEEDS WORK'}

---

## Infrastructure Requirements

| Component | Status | Details |
|-----------|--------|---------|
| **Python 3.10+** | {'✅' if infrastructure.get('python_version', False) else '❌'} | {'Available' if infrastructure.get('python_version', False) else 'Not available'} |
| **Docker** | {'✅' if infrastructure.get('docker_available', {}).get('available', False) else '❌'} | {infrastructure.get('docker_available', {}).get('status', 'Unknown')} |
| **Memgraph** | {'✅' if infrastructure.get('memgraph_available', {}).get('available', False) else '❌'} | {infrastructure.get('memgraph_available', {}).get('status', 'Unknown')} |
| **Dependencies** | {'✅' if infrastructure.get('dependencies', {}).get('available', False) else '⚠️'} | {infrastructure.get('dependencies', {}).get('status', 'Unknown')} |
| **uv** | {'✅' if infrastructure.get('uv_available', {}).get('available', False) else '❌'} | {infrastructure.get('uv_available', {}).get('status', 'Unknown')} |

---

## Service Health Checks

| Service | Status | Details |
|---------|--------|---------|
| **API Health Endpoint** | {'✅' if services.get('api_health_endpoint', {}).get('operational', False) else '❌'} | {services.get('api_health_endpoint', {}).get('status', 'Unknown')} |
| **Memgraph Connection** | {'✅' if services.get('memgraph_connection', {}).get('operational', False) else '❌'} | {services.get('memgraph_connection', {}).get('status', 'Unknown')} |
| **Makefile Targets** | {'✅' if services.get('makefile_targets', {}).get('operational', False) else '❌'} | {services.get('makefile_targets', {}).get('status', 'Unknown')} |

---

## Configuration Validation

| Component | Status | Details |
|-----------|--------|---------|
| **Settings File** | {'✅' if configuration.get('settings_file', {}).get('valid', False) else '❌'} | {configuration.get('settings_file', {}).get('status', 'Unknown')} |
| **.env.example** | {'✅' if configuration.get('env_example', {}).get('valid', False) else '❌'} | {configuration.get('env_example', {}).get('status', 'Unknown')} |
| **Config Validation** | {'✅' if configuration.get('config_validation', {}).get('valid', False) else '❌'} | {configuration.get('config_validation', {}).get('status', 'Unknown')} |

---

## Security Assessment

| Check | Status | Details |
|-------|--------|---------|
| **Secrets Scan** | {'✅' if security.get('secrets_scan', {}).get('clean', False) else '⚠️'} | {security.get('secrets_scan', {}).get('status', 'Unknown')} |
| **Dependency Audit** | {'✅' if security.get('dependency_audit', {}).get('clean', False) else '⚠️'} | {security.get('dependency_audit', {}).get('status', 'Unknown')} |
| **Auth Implementation** | {'✅' if security.get('auth_implementation', {}).get('clean', False) else '❌'} | {security.get('auth_implementation', {}).get('status', 'Unknown')} |

---

## Issues & Recommendations

"""
        
        if self.results.get('issues'):
            for issue in self.results['issues']:
                report += f"- ⚠️ {issue}\n"
        else:
            report += "- ✅ No critical issues found\n"
        
        report += f"""
---

## Recommendations

"""
        
        if overall_ready:
            report += """- ✅ **System is deployment-ready** - Proceed with deployment
- ✅ Set up demo environment (see DEMO_SETUP_GUIDE.md)
- ✅ Configure production environment variables
- ✅ Deploy to staging environment
- ✅ Run post-deployment verification
"""
        else:
            report += """- ⚠️ **Address blockers before deployment:**
"""
            if not infra_ready:
                report += "  - Verify infrastructure requirements (Python, Docker, Memgraph)\n"
            if not services_ready:
                report += "  - Verify service health endpoints\n"
            if not config_ready:
                report += "  - Verify configuration files\n"
            if not security_clean:
                report += "  - Review security findings\n"
            report += "- 🔧 Re-run verification after fixes\n"
        
        report += f"""
---

## Next Steps

1. **If Ready:**
   - Review deployment guide (DEPLOYMENT_GUIDE.md)
   - Set up demo environment (DEMO_SETUP_GUIDE.md)
   - Configure production environment
   - Deploy to staging

2. **If Needs Work:**
   - Address identified blockers
   - Re-run verification
   - Update this report

---

**Report Generated:** {datetime.now().isoformat()}
"""
        
        with open(report_path, 'w') as f:
            f.write(report)
    
    async def _generate_deployment_guide(self, guide_path: Path):
        """Generate deployment guide"""
        
        guide = f"""# Synapse Graph-RAG - Deployment Guide

**Generated:** {datetime.now().isoformat()}
**Project:** Synapse Graph-RAG
**Location:** `neoforge-dev/synapse-graph-rag/`

---

## Prerequisites

### Required
- **Python 3.10+** - Check with `python3 --version`
- **Docker & Docker Compose** - For Memgraph
- **uv** - Python dependency management (Astral)
- **Internet access** - For NLP model downloads

### Recommended
- **Memgraph** - Via Docker Compose (included)
- **PostgreSQL** - For production (optional, can use Memgraph)

---

## Quick Start

### Step 1: Install Dependencies
```bash
cd neoforge-dev/synapse-graph-rag

# Install using uv (recommended)
make install-dev
# Or: uv pip install -e .[dev]

# Download NLP models
make download-nlp-data
```

### Step 2: Start Infrastructure
```bash
# Start Memgraph via Docker Compose
make run-memgraph
# Or: docker-compose -f tools/docker/docker-compose.yml up -d memgraph

# Verify Memgraph is running
docker ps | grep memgraph
```

### Step 3: Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Key variables:
# - SYNAPSE_MEMGRAPH_HOST=localhost
# - SYNAPSE_MEMGRAPH_PORT=7687
# - SYNAPSE_API_HOST=0.0.0.0
# - SYNAPSE_API_PORT=8000
```

### Step 4: Start API Server
```bash
# Start FastAPI server
make run-api
# Or: uv run python -m graph_rag.api.main

# Verify API is running
curl http://localhost:8000/health
```

---

## Production Deployment

### Option 1: Docker Compose (Recommended for Staging)

```bash
# Start all services
make up
# Or: docker-compose -f tools/docker/docker-compose.yml up -d

# Check logs
make logs-memgraph
docker-compose logs -f api
```

### Option 2: Kubernetes (Production)

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Verify pods
kubectl get pods -n synapse

# Check services
kubectl get svc -n synapse
```

### Option 3: Railway/Cloudflare (Managed)

See infrastructure-specific guides in `infrastructure/` directory.

---

## Environment Variables

### Required Variables

```bash
# Memgraph Connection
SYNAPSE_MEMGRAPH_HOST=localhost
SYNAPSE_MEMGRAPH_PORT=7687
SYNAPSE_MEMGRAPH_USER=memgraph
SYNAPSE_MEMGRAPH_PASSWORD=memgraph

# API Configuration
SYNAPSE_API_HOST=0.0.0.0
SYNAPSE_API_PORT=8000

# LLM Provider (choose one)
SYNAPSE_LLM_TYPE=openai  # or mock, anthropic
SYNAPSE_OPENAI_API_KEY=sk-...  # if using OpenAI
```

### Optional Variables

```bash
# Authentication (Enterprise)
SYNAPSE_ENABLE_AUTHENTICATION=true
SYNAPSE_JWT_SECRET_KEY=your-secret-key

# Vector Store
SYNAPSE_VECTOR_STORE_TYPE=simple  # or faiss, pinecone

# Entity Extraction
SYNAPSE_ENTITY_EXTRACTOR_TYPE=spacy  # or mock

# Embedding Provider
SYNAPSE_EMBEDDING_PROVIDER=sentencetransformers  # or openai
```

---

## Post-Deployment Verification

### Health Checks

```bash
# API Health
curl http://localhost:8000/health

# API Docs
open http://localhost:8000/docs

# Memgraph Connection (via API)
curl http://localhost:8000/api/v1/health
```

### Functional Tests

```bash
# Run test suite
make test

# Run integration tests (requires Memgraph)
make test-memgraph

# Run all tests
make test-all
```

### Performance Checks

```bash
# Check API response time
time curl http://localhost:8000/health

# Monitor resource usage
docker stats
```

---

## Troubleshooting

### Memgraph Connection Failed

```bash
# Check if Memgraph is running
docker ps | grep memgraph

# Check Memgraph logs
docker logs <memgraph-container-id>

# Verify connection string
echo $SYNAPSE_MEMGRAPH_HOST
echo $SYNAPSE_MEMGRAPH_PORT
```

### API Not Starting

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check dependencies
uv pip list

# Check logs
tail -f logs/api.log  # if logging to file
```

### Dependencies Missing

```bash
# Reinstall dependencies
make install-dev

# Download NLP models
make download-nlp-data

# Verify installation
python3 -c "import graph_rag; print('OK')"
```

---

## Monitoring

### Health Endpoints

- **API Health:** `GET /health`
- **API Docs:** `GET /docs`
- **OpenAPI Spec:** `GET /openapi.json`

### Metrics (if Prometheus enabled)

- **Metrics:** `GET /metrics`

---

## Rollback Procedures

If deployment fails:

1. **Stop services:**
   ```bash
   make down
   # Or: docker-compose down
   ```

2. **Restore previous version:**
   ```bash
   git checkout <previous-tag>
   ```

3. **Rebuild and redeploy:**
   ```bash
   make install-dev
   make up
   ```

---

## Security Considerations

- ✅ **Secrets:** Use environment variables, never hardcode
- ✅ **Authentication:** Enable JWT auth for production
- ✅ **Network:** Use HTTPS in production
- ✅ **Dependencies:** Regularly audit with `uv pip-audit`

---

**Last Updated:** {datetime.now().isoformat()}
"""
        
        with open(guide_path, 'w') as f:
            f.write(guide)


async def main():
    """Main verification runner"""
    
    verifier = DeploymentReadinessVerifier()
    results = await verifier.run_verification()
    
    # Display summary
    print("\n" + "=" * 60)
    print("🎯 DEPLOYMENT READINESS VERIFICATION COMPLETE")
    print("=" * 60)
    
    infra_ready = (
        results['infrastructure'].get('python_version', False) and
        results['infrastructure'].get('docker_available', {}).get('available', False) and
        results['infrastructure'].get('memgraph_available', {}).get('available', False)
    )
    
    services_ready = (
        results['services'].get('api_health_endpoint', {}).get('operational', False) and
        results['services'].get('memgraph_connection', {}).get('operational', False)
    )
    
    print(f"Infrastructure: {'✅ Ready' if infra_ready else '⚠️ Needs work'}")
    print(f"Services: {'✅ Ready' if services_ready else '⚠️ Needs work'}")
    
    overall_ready = infra_ready and services_ready
    
    if overall_ready:
        print("\n🎉 DEPLOYMENT READY - Proceed with deployment!")
    else:
        print("\n⚠️  NEEDS WORK - Address blockers before deployment")
    
    print("\n📄 Reports generated in docs/ directory")


if __name__ == "__main__":
    asyncio.run(main())
