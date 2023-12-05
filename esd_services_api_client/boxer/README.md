# Boxer API Connector

Conenctor for working with [Boxer](https://github.com/SneaksAndData/boxer) AuthZ/AuthN API. 

## Usage

Two environment variables must be set before you can use this connector:

```shell
export BOXER_CONSUMER_ID="my_app_consumer"
export BOXER_PRIVATE_KEY="MIIEpAIBAA..."
```

### Retrieving Claims:

```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
resp = conn.get_claims("adma@ecco.com", "azuread")
for claim in resp:
    print(claim.to_dict())
```

### Insert a claim:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
claim_to_insert = Claim("some-test.test.sneaksanddata.com", ".*")
resp = conn.add_claim("adma@ecco.com", "azuread", claim_to_insert)
print(resp)
```

### Remove a claim:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
claim_to_remove = Claim("some-test.test.sneaksanddata.com", ".*")
resp = conn.remove_claim("adma@ecco.com", "azuread", claim_to_remove)
print(resp)
```

### Add a user:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
resp = conn.add_user("test@ecco.com", "azuread")
print(resp)
```

### Remove a user:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
resp = conn.remove_user("test@ecco.com", "azuread")
```

### Using as an authentication provider for other connectors
```python
from esd_services_api_client.boxer import BoxerConnector, RefreshableExternalTokenAuth, BoxerTokenAuth
from esd_services_api_client.crystal import CrystalConnector

auth_method = "example"

def get_external_token() -> str:
    return "example_token"

# Configure authentication with boxer
external_auth = RefreshableExternalTokenAuth(lambda: get_external_token(), auth_method)
boxer_connector = BoxerConnector(base_url="https://example.com", auth=external_auth)

# Inject boxer auth to Crystal connector
connector = CrystalConnector(base_url="https://example.com", auth=BoxerTokenAuth(boxer_connector))

# Use Crystal connector with boxer auth
connector.await_runs("algorithm", ["id"])
```
