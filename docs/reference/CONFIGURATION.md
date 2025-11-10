# Synapse Configuration Reference

**Complete Environment Variables Guide**
**Last Updated**: 2025-11-10 (Week 45 Performance Optimization Sprint Complete)

---

## Overview

Synapse uses the `SYNAPSE_` prefix for all environment variables. Configuration can be provided via:
- Environment variables
- `.env` file in the project root
- System environment

**Configuration Loading Priority** (highest to lowest):
1. Explicitly set environment variables
2. `.env` file values
3. Default values from Settings class

---

## Quick Start

### Minimal Configuration

```bash
# .env file for local development
SYNAPSE_API_PORT=8000
SYNAPSE_MEMGRAPH_HOST=127.0.0.1
SYNAPSE_VECTOR_STORE_TYPE=simple
SYNAPSE_LLM_TYPE=mock
SYNAPSE_ENABLE_AUTHENTICATION=false  # Disable for dev
```

### Production Configuration

```bash
# .env file for production
SYNAPSE_API_HOST=0.0.0.0
SYNAPSE_API_PORT=8000
SYNAPSE_API_LOG_JSON=true

# Security
SYNAPSE_JWT_SECRET_KEY=<generate-random-32-char-string>
SYNAPSE_ENABLE_AUTHENTICATION=true

# Graph Database
SYNAPSE_MEMGRAPH_HOST=memgraph.production.internal
SYNAPSE_MEMGRAPH_PORT=7687
SYNAPSE_MEMGRAPH_USE_SSL=true

# Vector Store
SYNAPSE_VECTOR_STORE_TYPE=faiss
SYNAPSE_USE_OPTIMIZED_FAISS=true
SYNAPSE_FAISS_USE_GPU=true
SYNAPSE_FAISS_QUANTIZE=true

# LLM
SYNAPSE_LLM_TYPE=openai
SYNAPSE_OPENAI_API_KEY=<your-api-key>
SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini

# Monitoring
SYNAPSE_ENABLE_METRICS=true
SYNAPSE_ENABLE_RATE_LIMITING=true
```

---

## Configuration Categories

### 1. API Server Configuration

**SYNAPSE_API_HOST**
- **Type**: string
- **Default**: `0.0.0.0`
- **Description**: Host address for the FastAPI server
- **Production**: `0.0.0.0` (all interfaces)
- **Development**: `127.0.0.1` (localhost only)

**SYNAPSE_API_PORT**
- **Type**: integer
- **Default**: `8000`
- **Description**: Port number for the FastAPI server
- **Range**: 1-65535
- **Note**: Use 18888 when running via `synapse up`

**SYNAPSE_API_LOG_LEVEL**
- **Type**: string
- **Default**: `INFO`
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Description**: Logging level for the API server
- **Development**: `DEBUG` for detailed logs
- **Production**: `INFO` or `WARNING`

**SYNAPSE_API_LOG_JSON**
- **Type**: boolean
- **Default**: `false`
- **Description**: Emit structured JSON logs
- **Production**: `true` for log aggregation (ELK, Splunk)
- **Development**: `false` for readable console logs

---

### 2. Security & Authentication

**SYNAPSE_JWT_SECRET_KEY**
- **Type**: string (SecretStr)
- **Default**: `None`
- **Description**: JWT secret key for token signing
- **Required**: When authentication is enabled
- **Security**: Must be at least 32 characters, randomly generated
- **Example**: `openssl rand -base64 32`

**SYNAPSE_JWT_ALGORITHM**
- **Type**: string
- **Default**: `HS256`
- **Options**: `HS256`, `HS384`, `HS512`, `RS256`, `RS384`, `RS512`
- **Description**: Algorithm for JWT token signing
- **Note**: RSxxx requires private/public key pair

**SYNAPSE_JWT_ACCESS_TOKEN_EXPIRE_MINUTES**
- **Type**: integer
- **Default**: `30`
- **Range**: 5-1440 (5 minutes to 24 hours)
- **Description**: JWT access token expiration in minutes
- **Security**: Shorter = more secure, but more frequent re-auth

**SYNAPSE_ENABLE_AUTHENTICATION**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable authentication for API endpoints
- **Development**: `false` for easier testing
- **Production**: `true` always

**SYNAPSE_REQUIRE_AUTH_FOR_DOCS**
- **Type**: boolean
- **Default**: `false`
- **Description**: Require authentication to access /docs, /redoc
- **Production**: `true` for internal APIs

---

### 3. Graph Database (Memgraph)

**SYNAPSE_DISABLE_GRAPH**
- **Type**: boolean
- **Default**: `false`
- **Description**: Disable graph functionality (vector-only mode)
- **Use Case**: When Memgraph unavailable

**SYNAPSE_MEMGRAPH_HOST**
- **Type**: string
- **Default**: `127.0.0.1`
- **Description**: Hostname or IP address of Memgraph instance
- **Docker**: Use service name (e.g., `memgraph`)
- **Production**: Use FQDN or IP

**SYNAPSE_MEMGRAPH_PORT**
- **Type**: integer
- **Default**: `7687`
- **Description**: Bolt protocol port for Memgraph
- **Standard**: 7687 (Bolt), 7444 (HTTP)

**SYNAPSE_MEMGRAPH_USER**
- **Type**: string
- **Default**: `None`
- **Description**: Username for Memgraph connection
- **Note**: Memgraph defaults to no auth

**SYNAPSE_MEMGRAPH_PASSWORD**
- **Type**: string (SecretStr)
- **Default**: `None`
- **Description**: Password for Memgraph connection

**SYNAPSE_MEMGRAPH_USE_SSL**
- **Type**: boolean
- **Default**: `false`
- **Description**: Use SSL/TLS for Memgraph connection
- **Production**: `true` for remote connections

**SYNAPSE_MEMGRAPH_MAX_RETRIES**
- **Type**: integer
- **Default**: `3`
- **Range**: 0-10
- **Description**: Maximum connection/query retries

**SYNAPSE_MEMGRAPH_RETRY_DELAY**
- **Type**: integer
- **Default**: `2`
- **Range**: 1-60
- **Description**: Delay in seconds between retries

---

### 4. Vector Store Configuration

**SYNAPSE_VECTOR_STORE_TYPE**
- **Type**: string
- **Default**: `simple`
- **Options**: `simple`, `faiss`, `mock`
- **Description**: Type of vector store to use
- **Development**: `simple` (in-memory)
- **Production**: `faiss` (optimized)
- **Testing**: `mock` (no actual storage)

**SYNAPSE_VECTOR_STORE_PATH**
- **Type**: string
- **Default**: `~/.graph_rag/vector_store`
- **Description**: Filesystem path for persistent vector store data
- **Note**: Auto-created if doesn't exist

**SYNAPSE_SIMPLE_VECTOR_STORE_PERSISTENT**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable persistence for simple vector store
- **Note**: Shares data between processes when true

**SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL**
- **Type**: string
- **Default**: `all-MiniLM-L6-v2`
- **Options**: Any sentence-transformers model
- **Description**: Embedding model for vector store
- **Popular Models**:
  - `all-MiniLM-L6-v2` (384 dim, fast, good quality)
  - `all-mpnet-base-v2` (768 dim, slower, better quality)
  - `paraphrase-multilingual-MiniLM-L12-v2` (384 dim, multilingual)

---

### 5. FAISS Optimization Settings

**SYNAPSE_USE_OPTIMIZED_FAISS**
- **Type**: boolean
- **Default**: `true`
- **Description**: Use optimized FAISS for 10x+ performance
- **Production**: `true` always
- **Development**: `true` (unless debugging)

**SYNAPSE_FAISS_USE_GPU**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable GPU acceleration when available
- **Requires**: CUDA-capable GPU, faiss-gpu package
- **Auto-Fallback**: Falls back to CPU if GPU unavailable

**SYNAPSE_FAISS_QUANTIZE**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable product quantization for memory efficiency
- **Memory Savings**: 4-8x reduction
- **Accuracy**: ~95% of full precision

**SYNAPSE_FAISS_NLIST**
- **Type**: integer
- **Default**: `100`
- **Range**: 1-10000
- **Description**: Number of clusters for IVF indexing
- **Recommendation**: sqrt(N) where N = number of vectors
- **Example**: 10K vectors → nlist=100, 1M vectors → nlist=1000

**SYNAPSE_FAISS_M**
- **Type**: integer
- **Default**: `16`
- **Range**: 4-64
- **Description**: Number of connections for HNSW indexing
- **Tradeoff**: Higher = better accuracy, more memory
- **Common Values**: 8 (fast), 16 (balanced), 32 (accurate)

**SYNAPSE_FAISS_EF_CONSTRUCTION**
- **Type**: integer
- **Default**: `200`
- **Range**: 16-1000
- **Description**: HNSW construction quality parameter
- **Tradeoff**: Higher = better quality, slower build
- **Recommendation**: 2x to 4x of M value

**SYNAPSE_FAISS_EF_SEARCH**
- **Type**: integer
- **Default**: `50`
- **Range**: 1-1000
- **Description**: HNSW search quality parameter
- **Tradeoff**: Higher = better accuracy, slower search
- **Recommendation**: 10-100 for most use cases

---

### 6. NLP & Entity Extraction

**SYNAPSE_ENTITY_EXTRACTOR_TYPE**
- **Type**: string
- **Default**: `spacy`
- **Options**: `mock`, `spacy`
- **Description**: Type of entity extractor
- **Development**: `mock` (fast, no dependencies)
- **Production**: `spacy` (accurate NER)

**SYNAPSE_ENTITY_EXTRACTOR_MODEL**
- **Type**: string
- **Default**: `en_core_web_sm`
- **Options**: Any spaCy model
- **Description**: spaCy model name for entity extraction
- **Models**:
  - `en_core_web_sm` (12 MB, fast)
  - `en_core_web_md` (40 MB, more accurate)
  - `en_core_web_lg` (560 MB, most accurate)
  - `en_core_web_trf` (transformer-based, slow, best accuracy)

**SYNAPSE_EMBEDDING_PROVIDER**
- **Type**: string
- **Default**: `sentence-transformers`
- **Options**: `mock`, `sentence-transformers`, `openai`, `ollama`
- **Description**: Provider for embedding generation

---

### 7. LLM Configuration

**SYNAPSE_LLM_TYPE**
- **Type**: string
- **Default**: `mock`
- **Options**: `mock`, `openai`, `anthropic`, `ollama`
- **Description**: LLM service type
- **Development**: `mock` (no API calls)
- **Production**: `openai`, `anthropic`, or `ollama`

**SYNAPSE_OPENAI_API_KEY**
- **Type**: string (SecretStr)
- **Default**: `None`
- **Description**: OpenAI API key
- **Required**: When llm_type=openai
- **Security**: Never commit to git

**SYNAPSE_ANTHROPIC_API_KEY**
- **Type**: string (SecretStr)
- **Default**: `None`
- **Description**: Anthropic API key
- **Required**: When llm_type=anthropic

**SYNAPSE_OLLAMA_BASE_URL**
- **Type**: string
- **Default**: `http://localhost:11434`
- **Description**: Ollama server URL
- **Docker**: Use service name

**SYNAPSE_LLM_MODEL_NAME**
- **Type**: string
- **Default**: `gpt-4o-mini`
- **Description**: Model name for LLM service
- **OpenAI**: `gpt-4o`, `gpt-4o-mini`, `gpt-3.5-turbo`
- **Anthropic**: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- **Ollama**: `llama2`, `mistral`, `codellama`

**SYNAPSE_LLM_MAX_TOKENS**
- **Type**: integer
- **Default**: `2000`
- **Range**: 1-100000 (model dependent)
- **Description**: Maximum tokens for LLM responses

**SYNAPSE_LLM_TEMPERATURE**
- **Type**: float
- **Default**: `0.3`
- **Range**: 0.0-2.0
- **Description**: Temperature for LLM generation
- **Recommendation**: 0.0-0.3 (factual), 0.7-1.0 (creative)

**SYNAPSE_LLM_TIMEOUT**
- **Type**: float
- **Default**: `30.0`
- **Range**: 1.0-300.0
- **Description**: Timeout in seconds for LLM API calls

---

### 8. Citation & Retrieval Settings

**SYNAPSE_CITATION_STYLE**
- **Type**: string
- **Default**: `numeric`
- **Options**: `numeric`, `apa`, `mla`, `chicago`, `ieee`
- **Description**: Citation style for generated answers

**SYNAPSE_GRAPH_CONTEXT_MAX_TOKENS**
- **Type**: integer
- **Default**: `1500`
- **Range**: 100-10000
- **Description**: Maximum context tokens from graph retrieval

---

### 9. Operational Mode

**SYNAPSE_VECTOR_ONLY_MODE**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable vector-only mode (no graph features)
- **Use Case**: Simplified setup without Memgraph

**SYNAPSE_AUTO_FALLBACK_VECTOR_MODE**
- **Type**: boolean
- **Default**: `true`
- **Description**: Auto-fallback to vector-only if graph unavailable
- **Recommendation**: `true` for resilience

---

### 10. Notion Integration

**SYNAPSE_NOTION_API_KEY**
- **Type**: string (SecretStr)
- **Default**: `None`
- **Description**: Notion API key for sync
- **Obtain**: https://www.notion.so/my-integrations

**SYNAPSE_NOTION_BASE_URL**
- **Type**: string
- **Default**: `https://api.notion.com/v1`
- **Description**: Notion API base URL

**SYNAPSE_NOTION_VERSION**
- **Type**: string
- **Default**: `2022-06-28`
- **Description**: Notion API version header

**SYNAPSE_NOTION_MAX_RETRIES**
- **Type**: integer
- **Default**: `5`
- **Range**: 0-10
- **Description**: Max retry attempts on Notion API failures

**SYNAPSE_NOTION_MAX_QPS**
- **Type**: float
- **Default**: `3.0`
- **Range**: 0.1-10.0
- **Description**: Max requests per second (client-side throttle)
- **Notion Limit**: 3 req/sec

**SYNAPSE_NOTION_BACKOFF_CEILING**
- **Type**: float
- **Default**: `8.0`
- **Range**: 0.5-60.0
- **Description**: Max exponential backoff seconds for 429 retries

---

### 11. Caching Configuration (Week 45 Performance Optimizations)

**Performance Benefits**:
- **Search Caching**: -200-400ms for repeated identical queries
- **Embedding Caching**: 30% faster ingestion for duplicate content
- **Entity Caching**: -20-48ms reduction per entity extraction
- **Combined Impact**: <100ms average cache hit, <200ms cache miss

**SYNAPSE_CACHE_TYPE**
- **Type**: string
- **Default**: `memory`
- **Options**: `memory`, `redis`
- **Description**: Cache backend type
- **Development**: `memory` (in-process)
- **Production**: `redis` (distributed)

**SYNAPSE_REDIS_URL**
- **Type**: string
- **Default**: `None`
- **Description**: Redis URL for caching
- **Format**: `redis://host:port/db`
- **Example**: `redis://localhost:6379/0`

**SYNAPSE_CACHE_DEFAULT_TTL**
- **Type**: integer
- **Default**: `300`
- **Description**: Default cache TTL in seconds (5 minutes)

**SYNAPSE_CACHE_EMBEDDING_TTL**
- **Type**: integer
- **Default**: `3600`
- **Description**: Embedding cache TTL in seconds (1 hour)

**SYNAPSE_CACHE_SEARCH_TTL**
- **Type**: integer
- **Default**: `600`
- **Description**: Search result cache TTL in seconds (10 minutes)

**SYNAPSE_EMBEDDING_CACHE_SIZE**
- **Type**: integer
- **Default**: `1000`
- **Range**: 1-10000
- **Description**: Maximum number of embeddings to cache in memory
- **Purpose**: Speeds up duplicate content embedding by 20-30%
- **Use Case**: Large ingestion with repeated content
- **Memory Impact**: ~400KB per 100 cached embeddings (384-dim vectors)

**SYNAPSE_ENTITY_CACHE_SIZE**
- **Type**: integer
- **Default**: `500`
- **Range**: 1-5000
- **Description**: Maximum number of entity extractions to cache
- **Purpose**: Reduces redundant spaCy processing (-20-48ms per query)
- **Recommendation**: Reduce if memory constrained, increase for large documents
- **Memory Impact**: Minimal (~10KB per 100 cached extractions)

**SYNAPSE_SEARCH_CACHE_SIZE**
- **Type**: integer
- **Default**: `100`
- **Range**: 1-1000
- **Description**: Maximum number of search results to cache
- **Purpose**: Speeds up repeated identical queries (-200-400ms)
- **TTL**: Controlled by SYNAPSE_CACHE_SEARCH_TTL
- **Memory Impact**: ~50KB per 100 cached search results

---

### 12. Document Processing

**SYNAPSE_CHUNK_SPLITTER_TYPE**
- **Type**: string
- **Default**: `sentence`
- **Options**: `sentence`, `token`
- **Description**: Chunk splitting strategy
- **sentence**: Split on sentence boundaries
- **token**: Split on token count

**SYNAPSE_INGESTION_CHUNK_SIZE**
- **Type**: integer
- **Default**: `200`
- **Range**: 50-2000
- **Description**: Target chunk size in tokens/sentences
- **Recommendation**: 150-300 for most use cases

**SYNAPSE_INGESTION_CHUNK_OVERLAP**
- **Type**: integer
- **Default**: `20`
- **Range**: 0-100
- **Description**: Token overlap between chunks
- **Purpose**: Preserve context across chunk boundaries

---

### 13. Feature Flags

**SYNAPSE_ENABLE_KEYWORD_STREAMING**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable NDJSON streaming for keyword search

**SYNAPSE_ENABLE_METRICS**
- **Type**: boolean
- **Default**: `true`
- **Description**: Expose /metrics Prometheus endpoint
- **Production**: `true` for monitoring

**SYNAPSE_ENABLE_RATE_LIMITING**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable rate limiting middleware
- **Production**: `true` for DoS protection

**SYNAPSE_RATE_LIMIT_PER_MINUTE**
- **Type**: integer
- **Default**: `300`
- **Description**: Max requests per minute per client

**SYNAPSE_RATE_LIMIT_PER_HOUR**
- **Type**: integer
- **Default**: `5000`
- **Description**: Max requests per hour per client

---

### 14. LLM Relationship Extraction

**SYNAPSE_ENABLE_LLM_RELATIONSHIPS**
- **Type**: boolean
- **Default**: `false`
- **Description**: Persist LLM-inferred relationships to graph
- **Cost**: Increases LLM API usage
- **Quality**: Discovers implicit relationships

**SYNAPSE_LLM_REL_MIN_CONFIDENCE**
- **Type**: float
- **Default**: `0.7`
- **Range**: 0.0-1.0
- **Description**: Minimum confidence to persist relationships
- **Recommendation**: 0.6-0.8 for most use cases

---

### 15. Maintenance Jobs

**SYNAPSE_ENABLE_MAINTENANCE_JOBS**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable background maintenance jobs
- **Jobs**: FAISS index rebuilding, integrity checks
- **Production**: `true` with careful scheduling

**SYNAPSE_MAINTENANCE_INTERVAL_SECONDS**
- **Type**: integer
- **Default**: `86400` (1 day)
- **Range**: 60-604800
- **Description**: Interval between maintenance runs

---

### 16. Enterprise Authentication (90+ Variables)

#### Enterprise Features

**SYNAPSE_ENABLE_ENTERPRISE_AUTH**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable enterprise SSO, multi-tenancy, compliance

**SYNAPSE_ENABLE_MULTI_TENANCY**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable multi-tenant architecture

**SYNAPSE_DEFAULT_TENANT_DOMAIN**
- **Type**: string
- **Default**: `synapse.local`
- **Description**: Default tenant domain for single-tenant

**SYNAPSE_TENANT_ISOLATION_LEVEL**
- **Type**: string
- **Default**: `database`
- **Options**: `database`, `schema`, `row`
- **Description**: Tenant data isolation level

#### SAML 2.0

**SYNAPSE_SAML_ENTITY_ID**
- **Type**: string
- **Default**: `""`
- **Description**: SAML Service Provider Entity ID

**SYNAPSE_SAML_CERT_FILE**
- **Type**: string
- **Default**: `None`
- **Description**: Path to SAML X.509 certificate

**SYNAPSE_SAML_KEY_FILE**
- **Type**: string
- **Default**: `None`
- **Description**: Path to SAML private key

#### OAuth 2.0

**SYNAPSE_OAUTH_REDIRECT_URI**
- **Type**: string
- **Default**: `http://localhost:8000/auth/enterprise/oauth/callback`
- **Description**: OAuth redirect URI for callbacks

#### LDAP/Active Directory

**SYNAPSE_LDAP_CONNECTION_TIMEOUT**
- **Type**: integer
- **Default**: `10`
- **Range**: 1-60
- **Description**: LDAP connection timeout in seconds

**SYNAPSE_LDAP_SEARCH_TIMEOUT**
- **Type**: integer
- **Default**: `30`
- **Range**: 1-300
- **Description**: LDAP search timeout in seconds

#### Multi-Factor Authentication

**SYNAPSE_MFA_ISSUER_NAME**
- **Type**: string
- **Default**: `Synapse Graph-RAG`
- **Description**: Issuer name for TOTP tokens

**SYNAPSE_MFA_BACKUP_CODE_LENGTH**
- **Type**: integer
- **Default**: `8`
- **Range**: 6-12
- **Description**: Length of MFA backup codes

**SYNAPSE_MFA_TOTP_WINDOW**
- **Type**: integer
- **Default**: `1`
- **Range**: 0-5
- **Description**: TOTP time window tolerance

#### Compliance & Audit

**SYNAPSE_ENABLE_AUDIT_LOGGING**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable comprehensive audit logging

**SYNAPSE_AUDIT_LOG_ENCRYPTION**
- **Type**: boolean
- **Default**: `true`
- **Description**: Encrypt audit logs for tamper-evidence

**SYNAPSE_AUDIT_RETENTION_DAYS**
- **Type**: integer
- **Default**: `2555` (7 years)
- **Range**: 30-3650
- **Description**: Audit log retention period

**SYNAPSE_GDPR_COMPLIANCE_MODE**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable GDPR compliance with data subject rights

#### Security Policies

**SYNAPSE_PASSWORD_MIN_LENGTH**
- **Type**: integer
- **Default**: `12`
- **Range**: 8-128
- **Description**: Minimum password length

**SYNAPSE_SESSION_TIMEOUT_MINUTES**
- **Type**: integer
- **Default**: `30`
- **Range**: 5-1440
- **Description**: Session timeout in minutes

**SYNAPSE_MAX_CONCURRENT_SESSIONS**
- **Type**: integer
- **Default**: `5`
- **Range**: 1-100
- **Description**: Max concurrent sessions per user

**SYNAPSE_REQUIRE_MFA_FOR_ADMIN**
- **Type**: boolean
- **Default**: `true`
- **Description**: Require MFA for admin users

#### Enterprise Rate Limiting

**SYNAPSE_ENTERPRISE_RATE_LIMIT_PER_MINUTE**
- **Type**: integer
- **Default**: `1000`
- **Range**: 10-100000
- **Description**: Enterprise API rate limit per minute

**SYNAPSE_LOGIN_ATTEMPT_LIMIT**
- **Type**: integer
- **Default**: `5`
- **Range**: 3-20
- **Description**: Max failed login attempts before lockout

**SYNAPSE_LOCKOUT_DURATION_MINUTES**
- **Type**: integer
- **Default**: `30`
- **Range**: 5-1440
- **Description**: Account lockout duration

#### Encryption & Key Management

**SYNAPSE_ENABLE_FIELD_ENCRYPTION**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable field-level encryption for sensitive data

**SYNAPSE_ENCRYPTION_ALGORITHM**
- **Type**: string
- **Default**: `AES-256-GCM`
- **Options**: `AES-256-GCM`, `AES-256-CBC`, `ChaCha20-Poly1305`
- **Description**: Encryption algorithm for sensitive data

**SYNAPSE_KEY_ROTATION_INTERVAL_DAYS**
- **Type**: integer
- **Default**: `90`
- **Range**: 30-365
- **Description**: Encryption key rotation interval

#### High Availability & DR

**SYNAPSE_ENABLE_HA_MODE**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable high availability mode with failover

**SYNAPSE_BACKUP_ENCRYPTION**
- **Type**: boolean
- **Default**: `true`
- **Description**: Enable encryption of backups

**SYNAPSE_BACKUP_RETENTION_DAYS**
- **Type**: integer
- **Default**: `30`
- **Range**: 7-365
- **Description**: Backup retention period in days

**SYNAPSE_CROSS_REGION_REPLICATION**
- **Type**: boolean
- **Default**: `false`
- **Description**: Enable cross-region data replication for DR

---

## Environment Variable Aliases

Synapse supports legacy environment variable names for compatibility:

### Graph Database Aliases

- `GRAPH_DB_URI` → Parses into `SYNAPSE_MEMGRAPH_HOST`, `SYNAPSE_MEMGRAPH_PORT`, `SYNAPSE_MEMGRAPH_USE_SSL`
- `NEO4J_USERNAME` → `SYNAPSE_MEMGRAPH_USER`
- `NEO4J_PASSWORD` → `SYNAPSE_MEMGRAPH_PASSWORD`

### Logging Aliases

- `SYNAPSE_JSON_LOGS` → `SYNAPSE_API_LOG_JSON`

**Note**: SYNAPSE_ prefixed variables take precedence over aliases.

---

## Configuration Examples

### Development Setup

```bash
# .env for local development
SYNAPSE_API_PORT=8000
SYNAPSE_API_LOG_LEVEL=DEBUG
SYNAPSE_ENABLE_AUTHENTICATION=false

SYNAPSE_MEMGRAPH_HOST=localhost
SYNAPSE_MEMGRAPH_PORT=7687

SYNAPSE_VECTOR_STORE_TYPE=simple
SYNAPSE_SIMPLE_VECTOR_STORE_PERSISTENT=true

SYNAPSE_ENTITY_EXTRACTOR_TYPE=mock
SYNAPSE_LLM_TYPE=mock
```

### Production Setup

```bash
# .env for production
SYNAPSE_API_HOST=0.0.0.0
SYNAPSE_API_PORT=8000
SYNAPSE_API_LOG_LEVEL=INFO
SYNAPSE_API_LOG_JSON=true

SYNAPSE_JWT_SECRET_KEY=<generate-with-openssl-rand-base64-32>
SYNAPSE_ENABLE_AUTHENTICATION=true

SYNAPSE_MEMGRAPH_HOST=memgraph.internal
SYNAPSE_MEMGRAPH_PORT=7687
SYNAPSE_MEMGRAPH_USE_SSL=true

SYNAPSE_VECTOR_STORE_TYPE=faiss
SYNAPSE_USE_OPTIMIZED_FAISS=true
SYNAPSE_FAISS_USE_GPU=true
SYNAPSE_FAISS_QUANTIZE=true

SYNAPSE_LLM_TYPE=openai
SYNAPSE_OPENAI_API_KEY=<your-key>
SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini

SYNAPSE_ENABLE_METRICS=true
SYNAPSE_ENABLE_RATE_LIMITING=true
SYNAPSE_CACHE_TYPE=redis
SYNAPSE_REDIS_URL=redis://redis.internal:6379/0
```

### Enterprise Setup

```bash
# .env for enterprise deployment
# (Includes all production settings plus:)

SYNAPSE_ENABLE_ENTERPRISE_AUTH=true
SYNAPSE_ENABLE_MULTI_TENANCY=true
SYNAPSE_TENANT_ISOLATION_LEVEL=database

SYNAPSE_ENABLE_AUDIT_LOGGING=true
SYNAPSE_AUDIT_LOG_ENCRYPTION=true
SYNAPSE_GDPR_COMPLIANCE_MODE=true

SYNAPSE_REQUIRE_MFA_FOR_ADMIN=true
SYNAPSE_PASSWORD_MIN_LENGTH=16
SYNAPSE_SESSION_TIMEOUT_MINUTES=15

SYNAPSE_ENABLE_HA_MODE=true
SYNAPSE_CROSS_REGION_REPLICATION=true
```

---

## Configuration Validation

### Validate Configuration

```bash
# Check configuration without starting server
synapse config validate

# Show current configuration
synapse config show

# Generate .env template
synapse config generate-env > .env.example
```

### Common Configuration Errors

**1. Missing JWT Secret in Production**
```
Error: JWT secret key required when authentication enabled
Solution: Set SYNAPSE_JWT_SECRET_KEY=<random-32-char-string>
```

**2. Memgraph Connection Failed**
```
Error: Failed to connect to Memgraph at 127.0.0.1:7687
Solution: Check SYNAPSE_MEMGRAPH_HOST and ensure Memgraph is running
```

**3. Invalid Vector Store Type**
```
Error: Invalid vector_store_type: 'fast'
Solution: Use 'simple', 'faiss', or 'mock'
```

**4. OpenAI API Key Missing**
```
Error: OpenAI API key required when llm_type=openai
Solution: Set SYNAPSE_OPENAI_API_KEY=<your-key>
```

---

## Security Best Practices

1. **Never Commit Secrets**
   - Add `.env` to `.gitignore`
   - Use secret management (Vault, AWS Secrets Manager)

2. **Rotate Keys Regularly**
   - JWT secret: Every 90 days
   - API keys: Set expiration dates
   - Encryption keys: Automatic rotation

3. **Use Strong Secrets**
   ```bash
   # Generate secure JWT secret
   openssl rand -base64 32

   # Generate secure API key
   openssl rand -hex 32
   ```

4. **Principle of Least Privilege**
   - Disable features not needed
   - Use read-only database users where possible
   - Limit API rate limits appropriately

5. **Enable Production Security**
   - Always use `SYNAPSE_ENABLE_AUTHENTICATION=true`
   - Enable rate limiting
   - Use SSL/TLS for all connections
   - Enable audit logging

---

## Performance Tuning

### High-Traffic API

```bash
# Increase rate limits
SYNAPSE_RATE_LIMIT_PER_MINUTE=1000
SYNAPSE_RATE_LIMIT_PER_HOUR=50000

# Enable caching
SYNAPSE_CACHE_TYPE=redis
SYNAPSE_CACHE_SEARCH_TTL=600

# Optimize FAISS
SYNAPSE_FAISS_USE_GPU=true
SYNAPSE_FAISS_QUANTIZE=true
```

### Large Document Collections

```bash
# Optimize chunking
SYNAPSE_INGESTION_CHUNK_SIZE=150
SYNAPSE_INGESTION_CHUNK_OVERLAP=15

# Adjust FAISS parameters
SYNAPSE_FAISS_NLIST=1000  # For 1M+ vectors
SYNAPSE_FAISS_EF_SEARCH=100  # Higher accuracy

# Enable background maintenance
SYNAPSE_ENABLE_MAINTENANCE_JOBS=true
```

### Memory-Constrained Environments

```bash
# Use simple vector store
SYNAPSE_VECTOR_STORE_TYPE=simple

# Disable GPU
SYNAPSE_FAISS_USE_GPU=false

# Enable quantization
SYNAPSE_FAISS_QUANTIZE=true

# Reduce cache TTL
SYNAPSE_CACHE_DEFAULT_TTL=60
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-08
**Total Variables Documented**: 100+
**Categories**: 16
