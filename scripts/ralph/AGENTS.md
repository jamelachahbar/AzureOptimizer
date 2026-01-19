# Azure Cost Optimizer - Agent Instructions

## Project Overview

**Azure Cost Optimizer** is a Python/React application for optimizing Azure resource costs through policy-based automation. It combines cost analysis, anomaly detection, and automated remediation to help organizations reduce cloud spending.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ui/frontend/src/                                                │
│  ├── components/Optimizer.tsx (Main dashboard)                   │
│  ├── components/PolicyEditor.tsx (Policy CRUD)                   │
│  ├── components/PolicyTable.tsx (Policy display)                 │
│  └── hooks/useKeyboardShortcuts.ts                               │
├─────────────────────────────────────────────────────────────────┤
│                        Backend (Flask)                            │
│  ui/backend/                                                      │
│  ├── app.py (Main API - ~1400 lines)                             │
│  ├── azure_cost_optimizer/                                        │
│  │   ├── optimizer.py (Core engine - ~1800 lines)                │
│  │   ├── azure_clients.py (Client manager)                        │
│  │   ├── cache_manager.py (Caching layer)                         │
│  │   └── pagination.py (Pagination utilities)                     │
│  └── tests/ (Unit tests)                                          │
├─────────────────────────────────────────────────────────────────┤
│                        Infrastructure                             │
│  infra-azd/                                                       │
│  ├── main.bicep (Main deployment template)                       │
│  ├── main.bicepparam (Parameters)                                │
│  └── modules/ (Bicep modules for each resource)                  │
├─────────────────────────────────────────────────────────────────┤
│                        Policies (YAML)                            │
│  policies/policies.yaml                                           │
│  └── Schema: name, resource, filters[], actions[], enabled        │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, Flask, Azure SDK |
| **Frontend** | React 18, TypeScript, Fluent UI v9 |
| **Data** | Azure Blob Storage, Log Analytics |
| **ML** | scikit-learn (Isolation Forest for anomalies) |
| **Auth** | Microsoft Entra ID (Azure AD), MSAL |
| **Infrastructure** | Azure Container Apps, Azure Developer CLI (azd) |

## Key Files

### Backend
| File | Purpose |
|------|---------|
| `ui/backend/app.py` | Flask API routes, all `/api/*` endpoints |
| `ui/backend/azure_cost_optimizer/optimizer.py` | Core optimization logic, policy execution |
| `ui/backend/azure_cost_optimizer/azure_clients.py` | Azure SDK client manager |
| `ui/backend/azure_cost_optimizer/cache_manager.py` | In-memory caching with TTL |
| `policies/policies.yaml` | Policy definitions |

### Frontend
| File | Purpose |
|------|---------|
| `ui/frontend/src/Optimizer.tsx` | Main dashboard component |
| `ui/frontend/src/components/PolicyEditor.tsx` | Full CRUD policy editor |
| `ui/frontend/src/components/PolicyTable.tsx` | Read-only policy display |
| `ui/frontend/src/authConfig.ts` | MSAL authentication configuration |
| `ui/frontend/src/utils/apiConfig.ts` | API URL configuration |

### Infrastructure
| File | Purpose |
|------|---------|
| `infra-azd/main.bicep` | Main Bicep template |
| `infra-azd/modules/container-apps.bicep` | Container Apps configuration |
| `infra-azd/modules/app-registration.bicep` | Entra ID app registration |

## API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/health` | Health check with dependency status |
| GET | `/api/policies` | List all policies |
| POST | `/api/policies/validate` | Validate policy against schema |
| POST | `/api/policies/policyeditor/{name}` | Create new policy |
| PUT | `/api/policies/policyeditor/{name}` | Update existing policy |
| DELETE | `/api/policies/policyeditor/{name}` | Delete policy |
| GET | `/api/execution-data` | Get optimization execution history |
| GET | `/api/impacted-resources` | Get resources affected by policies |
| GET | `/api/cost-savings/estimate` | Estimate potential savings |
| GET | `/api/anomalies` | Get detected cost anomalies |
| POST | `/api/run` | Execute optimizer |
| GET | `/api/docs` | Swagger UI documentation |

## Policy Schema

```yaml
# Valid resource types and their allowed actions/filters

azure.vm:
  description: Stop or manage VMs based on CPU usage and tags
  actions: [stop, downgrade_disks, log]
  filters: [last_used, tag, stopped]

azure.disk:
  description: Delete unattached disks or downgrade SKU
  actions: [delete, downgrade_disks, log]
  filters: [unattached, tag, sku]

azure.resourcegroup:
  description: Delete entire resource groups by tag
  actions: [delete, log]
  filters: [tag]

azure.storage:
  description: Update storage SKU to reduce costs
  actions: [update_sku, log]
  filters: [tag, sku]

azure.sql:
  description: Scale SQL databases DTU during off-peak hours
  actions: [scale_dtu, log]
  filters: [tag]

azure.publicip:
  description: Delete unattached public IP addresses
  actions: [delete, log]
  filters: [unattached, tag]

azure.applicationgateway:
  description: Delete app gateways with empty backend pools
  actions: [delete, log]
  filters: [tag]

azure.nic:
  description: Delete unattached network interfaces
  actions: [delete, log]
  filters: [unattached, tag]
```

### Filter Details

| Filter | Description | Required Fields |
|--------|-------------|-----------------|
| `last_used` | VMs with low CPU usage over X days | `days`, `threshold` (optional, default 10%) |
| `unattached` | Resources not attached to anything | None |
| `tag` | Resources with specific tag key/value | `key`, `value` |
| `sku` | Resources with specific SKU names | `values` (array of SKU names) |
| `stopped` | VMs in deallocated state | None |

### Action Details

| Action | Description | Required Fields |
|--------|-------------|-----------------|
| `stop` | Stop/deallocate VMs | None |
| `delete` | Delete the resource | None |
| `downgrade_disks` | Change disk SKU to Standard_LRS | None |
| `update_sku` | Change storage account SKU | `sku` (target SKU name) |
| `scale_dtu` | Scale SQL database DTUs | `tiers` (array with tier configs) |
| `log` | Log only, no action taken | None |

## Development

### Testing

```powershell
# Backend tests
cd ui/backend
python -m pytest tests/ -v

# Frontend tests
cd ui/frontend
npm test

# Start backend locally
cd ui/backend
python app.py  # Runs on http://localhost:5000

# Start frontend locally
cd ui/frontend
npm run dev  # Runs on http://localhost:5173
```

### Deployment

```powershell
# Deploy with Azure Developer CLI
azd up

# Deploy only infrastructure
azd provision

# Deploy only application
azd deploy
```

## Code Patterns

### Backend (Python/Flask)
```python
# API route pattern
@app.route('/api/example', methods=['GET'])
def example_endpoint():
    try:
        # Implementation
        return jsonify({"data": result}), 200
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# Use DefaultAzureCredential
from azure.identity import DefaultAzureCredential
credential = DefaultAzureCredential()

# Use cache decorator
from azure_cost_optimizer.cache_manager import cache_manager
@cache_manager.cached(ttl=300)
def expensive_operation():
    pass
```

### Frontend (React/TypeScript)
```tsx
// Component pattern with Fluent UI v9
import { Button, Text, Card } from '@fluentui/react-components';

const MyComponent: React.FC<Props> = ({ prop }) => {
  const [state, setState] = useState<Type>(initial);

  useEffect(() => {
    // Side effects
  }, [dependencies]);

  return (
    <Card>
      <Text size={500}>Title</Text>
      <Button appearance="primary">Action</Button>
    </Card>
  );
};

// API calls use apiConfig for URL
import { getApiUrl } from '../utils/apiConfig';
const response = await axios.get(getApiUrl('/api/endpoint'));
```

## Important Notes

1. **API URLs**: Frontend uses `apiConfig.ts` to determine API URLs based on environment
2. **Policy Schema**: Each resource type has specific valid actions/filters - validate before saving
3. **One Policy Per Resource**: Only one policy allowed per resource type
4. **Azure Credentials**: Requires Azure CLI login or managed identity for authentication
5. **CORS**: Backend has CORS configured for frontend origins
6. **Authentication**: Frontend uses MSAL for Entra ID authentication; backend validates tokens

## Project Files Reference

- `scripts/ralph/prd.json` - Product backlog and feature definitions
- `scripts/ralph/progress.txt` - Implementation history and notes
- `QUICK_REFERENCE.md` - Quick setup commands
- `SETUP_SUMMARY.md` - Deployment configuration details
