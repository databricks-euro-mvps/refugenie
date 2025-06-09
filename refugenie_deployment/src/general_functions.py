from databricks.sdk import WorkspaceClient
from databricks.sdk.credentials_provider import ModelServingUserCredentials


def get_workspace_client(auth_type: str) -> object:
    """
    Returns an instance of WorkspaceClient based on the authentication type.

    Args:
        auth_type (str): The type of authentication to use. Must be 'system' or 'user'.

    Returns:
        WorkspaceClient: An instance of WorkspaceClient configured with the specified authentication type.
    """
    if auth_type == 'system':
        w = WorkspaceClient()
    elif auth_type == 'user':
        w = WorkspaceClient(credentials_strategy=ModelServingUserCredentials())
    else:
        raise ValueError("auth_type must be 'system' or 'user'")

    return w