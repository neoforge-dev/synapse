#!/bin/bash

# SSL/TLS Certificate Setup for PostgreSQL Production Infrastructure
# Generates self-signed certificates for secure connections

set -euo pipefail

# Configuration
CERT_DIR="/var/lib/postgresql/ssl"
COUNTRY="US"
STATE="California" 
CITY="San Francisco"
ORGANIZATION="Synapse Technologies"
OU="Database Infrastructure"
CN="postgres-primary"
DAYS=3650  # 10 years

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Create SSL directory
mkdir -p "${CERT_DIR}"
cd "${CERT_DIR}"

log "Setting up SSL certificates for PostgreSQL..."

# Generate private key
log "Generating private key..."
openssl genrsa -out server.key 4096
chmod 600 server.key
chown postgres:postgres server.key

# Generate certificate signing request
log "Generating certificate signing request..."
openssl req -new -key server.key -out server.csr -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORGANIZATION}/OU=${OU}/CN=${CN}"

# Generate self-signed certificate
log "Generating self-signed certificate..."
openssl x509 -req -in server.csr -signkey server.key -out server.crt -days ${DAYS}
chmod 644 server.crt
chown postgres:postgres server.crt

# Create certificate authority for client certificates
log "Creating certificate authority..."
openssl genrsa -out ca.key 4096
chmod 600 ca.key
chown postgres:postgres ca.key

openssl req -new -x509 -key ca.key -out ca.crt -days ${DAYS} \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORGANIZATION}/OU=Certificate Authority/CN=Synapse CA"
chmod 644 ca.crt
chown postgres:postgres ca.crt

# Generate client certificate for applications
log "Generating client certificates..."
openssl genrsa -out client.key 4096
chmod 600 client.key
chown postgres:postgres client.key

openssl req -new -key client.key -out client.csr \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORGANIZATION}/OU=Database Clients/CN=synapse_app"

openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -out client.crt -days ${DAYS} -CAcreateserial
chmod 644 client.crt
chown postgres:postgres client.crt

# Create certificate for PgBouncer
log "Generating PgBouncer certificates..."
openssl genrsa -out pgbouncer.key 4096
chmod 600 pgbouncer.key

openssl req -new -key pgbouncer.key -out pgbouncer.csr \
    -subj "/C=${COUNTRY}/ST=${STATE}/L=${CITY}/O=${ORGANIZATION}/OU=Connection Pool/CN=pgbouncer"

openssl x509 -req -in pgbouncer.csr -CA ca.crt -CAkey ca.key -out pgbouncer.crt -days ${DAYS} -CAcreateserial
chmod 644 pgbouncer.crt

# Create combined certificate for HAProxy
log "Creating combined certificate for HAProxy..."
cat server.crt server.key > haproxy.pem
chmod 600 haproxy.pem

# Clean up CSR files
rm -f *.csr *.srl

# Create certificate info file
cat > cert_info.txt << EOF
SSL Certificate Information
==========================
Generated: $(date)
Certificate Authority: Synapse CA
Server Certificate: server.crt/server.key
Client Certificate: client.crt/client.key  
PgBouncer Certificate: pgbouncer.crt/pgbouncer.key
HAProxy Combined: haproxy.pem

Certificate Validity: ${DAYS} days
Country: ${COUNTRY}
State: ${STATE}
City: ${CITY}
Organization: ${ORGANIZATION}

Usage:
- server.crt/key: PostgreSQL server SSL
- client.crt/key: Application SSL authentication
- pgbouncer.crt/key: PgBouncer SSL
- ca.crt: Certificate authority for client verification
- haproxy.pem: Combined cert for HAProxy SSL termination

Connection String Example:
postgresql://user:pass@host:5432/db?sslmode=require&sslcert=client.crt&sslkey=client.key&sslrootcert=ca.crt
EOF

log "SSL certificate setup completed successfully!"
log "Certificates created in: ${CERT_DIR}"
log "See cert_info.txt for usage information"

# Display certificate information
log "Server certificate details:"
openssl x509 -in server.crt -noout -text | grep -A 2 "Validity"
openssl x509 -in server.crt -noout -text | grep -A 1 "Subject:"