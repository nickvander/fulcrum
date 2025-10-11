# Production Setup Guide

This document provides essential notes and recommendations for deploying Fulcrum to a production environment.

## System-Level Configuration

### Redis: Memory Overcommit

When running the application with `docker compose up`, you may see the following warning from Redis:

```
WARNING Memory overcommit must be enabled! Without it, a background save or replication may fail under low memory condition...
```

**Recommendation:** For production deployments, it is highly recommended to enable memory overcommit on the host machine running the Docker containers. This ensures Redis can function reliably, especially under high memory pressure.

To fix this, add `vm.overcommit_memory = 1` to `/etc/sysctl.conf` on the host machine and then either reboot or run `sysctl vm.overcommit_memory=1`.
