"""
ROTA Connector interfaces package

These Abstract Base Classes define the contracts that consuming applications
must implement to bridge their own data models to the ROTA engine.

    IResourceProvider  →  generic for "staff" / schedulable entities
    IContextProvider   →  generic for "practice" / scheduling locations

Copyright (c) 2026 31 Green. All rights reserved.
"""

from rota_connector.interfaces.context_provider import IContextProvider
from rota_connector.interfaces.resource_provider import IResourceProvider

__all__ = [
    "IResourceProvider",
    "IContextProvider",
]
