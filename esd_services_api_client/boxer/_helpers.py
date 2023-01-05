""" Helper functions to parse responses
"""
from typing import Optional

from proteus.security.clients import AzureClient
from requests import Response

from esd_services_api_client.boxer import BoxerTokenAuth, ExternalTokenAuth, BoxerConnector
from esd_services_api_client.boxer._models import UserClaim, BoxerClaim


def _iterate_user_claims_response(user_claim_response: Response):
    """ Creates an iterator to iterate user claims from Json Response
    :param user_claim_response: HTTP Response containing json array of type UserClaim
    """
    response_json = user_claim_response.json()

    if response_json:
        for api_response_item in response_json:
            yield UserClaim.from_dict(api_response_item)
    else:
        raise ValueError('Expected response body of type application/json')


def _iterate_boxer_claims_response(boxer_claim_response: Response):
    """ Creates an iterator to iterate user claims from Json Response
    :param boxer_claim_response: HTTP Response containing json array of type BoxerClaim
    """
    response_json = boxer_claim_response.json()

    if response_json:
        for api_response_item in response_json:
            yield BoxerClaim.from_dict(api_response_item)
    else:
        raise ValueError('Expected response body of type application/json')


def select_authentication(auth_provider: str, env: str, subscription_id: str) -> Optional[BoxerTokenAuth]:
    """
    Select authentication provider for console clients in backward-compatible way
    This method will be removed after migration of console clients to boxer authentication
    :param auth_provider: Name of authorization provider
    :param env: Name of deploy environment
    :param subscription_id: Subscription id for 'azuread' authorization provider
    :return: BoxerAuthentication or None
    """
    auth = None
    if auth_provider == "azuread":
        proteus_client = AzureClient(subscription_id=subscription_id)
        external_auth = ExternalTokenAuth(proteus_client.get_access_token(), auth_provider)
        boxer_connector = BoxerConnector(base_url=f"https://boxer.{env}.sneaksanddata.com", auth=external_auth)
        auth = BoxerTokenAuth(boxer_connector)
    return auth
