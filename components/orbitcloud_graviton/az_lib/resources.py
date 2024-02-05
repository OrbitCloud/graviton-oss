def get_resource_name_from_id(resource_id: str) -> str:
    # Split the resource ID by '/' and take the last part as the resource name
    return resource_id.split("/")[-1]
