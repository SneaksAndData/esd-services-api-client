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
resp = conn.get_claims("email@ecco.com", "azuread")
for claim in resp:
    print(claim.to_dict())
```
Output:
```bash
{'claim_name':'test1.test.sneaksanddata.com/.*', 'claim_value':'.*'}
{'claim_name':'test2.test.sneaksanddata.com/.*', 'claim_value':'.*'}
```

### Insert claims:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
claims = [Claim("some-test-1.test.sneaksanddata.com", ".*"), Claim("some-test-2.test.sneaksanddata.com", ".*")]
resp = conn.add_claim("email@ecco.com", "azuread", claims)
print(resp)
```
Output:
```bash
ClaimResponse(identity_provider='azuread', user_id='email@ecco.com', claims=[{'some-test-1.test.sneaksanddata.com': '.*'}, {'some-test-2.test.sneaksanddata.com': '.*'}], billing_id= None}
```

### Remove claims:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
claims = [Claim("some-test-1.test.sneaksanddata.com", ".*"), Claim("some-test-2.test.sneaksanddata.com", ".*")]
resp = conn.remove_claim("email@ecco.com", "azuread", claims)
print(resp)
```
Output:
```bash
ClaimResponse(identity_provider='azuread', user_id='email@ecco.com', claims=[], billing_id= None}
```

### Add a user:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
resp = conn.add_user("test@ecco.com", "azuread")
print(resp)
```
Output:
```bash
ClaimResponse(identity_provider='azuread', user_id='test@ecco.com', claims=[], billing_id=None)
```

### Remove a user:
```python
from esd_services_api_client.boxer import select_authentication, BoxerClaimConnector, Claim
auth = select_authentication("azuread", "test")
conn = BoxerClaimConnector(base_url="https://boxer-claim.test.sneaksanddata.com", auth=auth)
resp = conn.remove_user("test@ecco.com", "azuread")
print(resp.status_code)
```
Output:
```bash
200
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
