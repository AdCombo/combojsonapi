import os
from typing import Generator, Tuple, Any, Type, Callable, Iterable

from flask_combo_jsonapi import Api
from marshmallow import Schema

from flask_combo_jsonapi.plugin import BasePlugin
from flask_combo_jsonapi.resource import Resource
from flask_combo_jsonapi.utils import SPLIT_REL
from flask_combo_jsonapi.exceptions import PluginMethodNotImplementedError

from combojsonapi.event.resource import EventsResource
from combojsonapi.utils import get_decorators_for_resource


class EventSchema(Schema):
    pass


class EventPlugin(BasePlugin):
    """Plugin for events routes in json_api"""

    def __init__(self, trailing_slash: bool = True):
        """

        :param trailing_slash: add trailing slash when creating events API
        """
        self.trailing_slash = trailing_slash

    @classmethod
    def _events_with_methods(cls, cls_events: Type[EventsResource]) -> Generator[Tuple[Any, str], None, None]:
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
                event_method = getattr(cls_events, attr_name)
                event_extra: dict = getattr(event_method, "extra", {})
                custom_method = event_extra.get("method")
                if custom_method:
                    method = custom_method
                yield event_method, method

    def _create_event_urls(self, urls: Iterable[str], event: Callable) -> Tuple[str]:
        """
        Create events with optional custom suffix
        """
        event_extra: dict = getattr(event, "extra", {})
        event_url_suffix = event_extra.get("url_suffix", event.__name__)

        event_urls = []
        for i_url in urls:
            i_new_url = os.path.join(i_url, event_url_suffix)
            i_new_url = i_new_url[:-1] if i_new_url[-1] == "/" else i_new_url
            i_new_url = i_new_url + "/" if self.trailing_slash else i_new_url
            event_urls.append(i_new_url)
        return tuple(event_urls)

    def _create_event_resource(self, base_resource: Type[Resource], event: Callable, method: str, view: str,
                               urls: Iterable[str], self_json_api: Api, **kwargs) -> None:
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

        event_urls = self._create_event_urls(urls, event)

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

    def before_route(self, resource: Type[Resource] = None, view: str = None, urls: Iterable[str] = None,
                     self_json_api: Api = None, **kwargs) -> None:
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
