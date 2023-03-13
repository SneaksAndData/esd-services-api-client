""" Helper functions to parse responses
"""
#  Copyright (c) 2023. ECCO Sneaks & Data
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

from requests import Response

from esd_services_api_client.boxer._models import UserClaim, BoxerClaim


def _iterate_user_claims_response(user_claim_response: Response):
    """Creates an iterator to iterate user claims from Json Response
    :param user_claim_response: HTTP Response containing json array of type UserClaim
    """
    response_json = user_claim_response.json()

    if response_json:
        for api_response_item in response_json:
            yield UserClaim.from_dict(api_response_item)
    else:
        raise ValueError("Expected response body of type application/json")


def _iterate_boxer_claims_response(boxer_claim_response: Response):
    """Creates an iterator to iterate user claims from Json Response
    :param boxer_claim_response: HTTP Response containing json array of type BoxerClaim
    """
    response_json = boxer_claim_response.json()

    if response_json:
        for api_response_item in response_json:
            yield BoxerClaim.from_dict(api_response_item)
    else:
        raise ValueError("Expected response body of type application/json")
