import urllib.parse
from typing import Generator, Tuple, Any

from marshmallow import Schema

from flask_combo_jsonapi.plugin import BasePlugin
from flask_combo_jsonapi.resource import Resource
from flask_combo_jsonapi.utils import SPLIT_REL
from flask_combo_jsonapi.exceptions import PluginMethodNotImplementedError

from combojsonapi.utils import get_decorators_for_resource


class EventSchema(Schema):
    pass


class EventPlugin(BasePlugin):
    def __init__(self, trailing_slash: bool = True):
        """

        :param trailing_slash: ставить ли закрывающий слеш у событийного API
        """
        self.trailing_slash = trailing_slash

    """Plugin for events routes in json_api"""

    @classmethod
    def _events_with_methods(cls, cls_events) -> Generator[Tuple[Any, str], None, None]:
        """
        Separates events by methods and returns them in pairs
        Like (event_get_enum, 'GET"), (event_post_data, 'POST'), ... etc
        :param cls_events:
        :return:
        """
        for attr_name in dir(cls_events):
            method = None
            if attr_name.startswith("event_get_"):
                method = "GET"
            elif attr_name.startswith("event_"):
                # Processing all other events. May be event_post_smth or just event_smth
                method = "POST"
            if method is not None:
                yield getattr(cls_events, attr_name), method

    def _create_event_resource(self, base_resource, event, method, view, urls, self_json_api, **kwargs):
        # noinspection PyTypeChecker
        new_resource: Resource = type(
            event.__name__,
            (base_resource,),
            {
                "methods": [method],
                "schema": None,
                method.lower(): event,
                "event": True,
            },
        )

        new_resource.decorators = get_decorators_for_resource(base_resource, self_json_api)

        i_view = f"{view}_{event.__name__}"
        view_func = new_resource.as_view(i_view)

        url_rule_options = kwargs.get("url_rule_options") or {}

        event_urls = []
        for i_url in urls:
            i_new_url = urllib.parse.urljoin(i_url, event.__name__)
            i_new_url = i_new_url[:-1] if i_new_url[-1] == "/" else i_new_url
            i_new_url = i_new_url + "/" if self.trailing_slash else i_new_url
            event_urls.append(i_new_url)
        event_urls = tuple(event_urls)

        if self_json_api.blueprint is not None:
            new_resource.view = SPLIT_REL.join([self_json_api.blueprint.name, new_resource.view])
            for url in event_urls:
                self_json_api.blueprint.add_url_rule(url, view_func=view_func, **url_rule_options)
        elif self_json_api.app is not None:
            for url in event_urls:
                self_json_api.app.add_url_rule(url, view_func=view_func, **url_rule_options)
        else:
            self_json_api.resources.append(
                {
                    "resource": new_resource,
                    "view": i_view,
                    "urls": event_urls,
                    "url_rule_options": url_rule_options,
                }
            )

        self_json_api.resource_registry.append(new_resource)

        for plugin in self_json_api.plugins:
            try:
                plugin.after_route(
                    view=view,
                    urls=event_urls,
                    self_json_api=self_json_api,
                    default_schema=None,
                    resource=new_resource,
                    **kwargs,
                )
            except PluginMethodNotImplementedError:
                pass

    def before_route(self, resource=None, view=None, urls=None, self_json_api=None, **kwargs):
        """
        :param resource:
        :param view:
        :param urls:
        :param self_json_api:
        :param kwargs:
        :return:
        """
        if not hasattr(resource, "events"):
            return

        for event, method in self._events_with_methods(resource.events):
            self._create_event_resource(resource, event, method, view, urls, self_json_api, **kwargs)
