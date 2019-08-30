def get_decorators_for_resource(resource, self_json_api) -> list:
    decorators = []
    if hasattr(resource, 'decorators'):
        decorators += list(resource.decorators)

    if getattr(resource, 'disable_global_decorators', False) is False:
        decorators += list(self_json_api.decorators)

    return decorators
