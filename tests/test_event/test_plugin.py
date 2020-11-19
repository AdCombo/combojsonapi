from unittest import mock

import pytest
from flask_combo_jsonapi import ResourceList, Api
from flask_combo_jsonapi.decorators import check_headers

from combojsonapi.event import EventPlugin
from combojsonapi.event.resource import EventsResource


class OkEvents(EventsResource):
    @classmethod
    def event_ok(cls):
        return 'ok'

    @classmethod
    def event_get_ok(cls):
        return 'ok'

    @classmethod
    def not_event(cls):
        pass


class SomeResourceList(ResourceList):
    pass


event_plugin = EventPlugin()

json_api = Api(plugins=[event_plugin])

json_api.route(SomeResourceList, 'some_resource', '/some_resource/')


class TestEventPlugin:
    @pytest.fixture(autouse=True)
    def clear_json_api_resources(self):
        yield
        json_api.resources = json_api.resources[:1]
        json_api.resource_registry = json_api.resource_registry[:1]

    @classmethod
    def _check_new_resource(cls, new_resource):
        assert issubclass(new_resource, ResourceList)
        assert new_resource.__name__ == OkEvents.event_ok.__name__
        assert new_resource.event
        assert new_resource.decorators == [check_headers]

    def test__events_with_methods(self):
        expected_results = [
            (OkEvents.event_get_ok, 'GET'),
            (OkEvents.event_ok, 'POST'),
        ]
        for i, result in enumerate(EventPlugin._events_with_methods(OkEvents)):
            assert result == expected_results[i]

    def test__create_event_resource(self):
        view, url = 'some_resource', '/some_resource/'
        event_plugin._create_event_resource(base_resource=SomeResourceList,
                                            event=OkEvents.event_ok,
                                            method='POST',
                                            view=view,
                                            urls=[url],
                                            self_json_api=json_api)
        assert len(json_api.resource_registry) == len(json_api.resources) == 2
        new_resource = json_api.resource_registry[-1]
        self._check_new_resource(new_resource)

        new_resource_dict = json_api.resources[-1]
        assert new_resource_dict['resource'] == new_resource
        assert new_resource_dict['view'] == f'{view}_{new_resource.__name__}'
        assert new_resource_dict['urls'][0] == f'{url}{new_resource.__name__}/'

    def test__create_event_resource__with_app(self):
        json_api.app = mock.Mock()
        view, url = 'some_resource', '/some_resource/'
        event_plugin._create_event_resource(base_resource=SomeResourceList,
                                            event=OkEvents.event_ok,
                                            method='POST',
                                            view=view,
                                            urls=[url],
                                            self_json_api=json_api)
        assert len(json_api.resource_registry) == 2
        new_resource = json_api.resource_registry[-1]
        self._check_new_resource(new_resource)

        assert len(json_api.resources) == 1  # shouldn't write to resources if app provided
        json_api.app.add_url_rule.assert_called_once()
        assert json_api.app.add_url_rule.call_args[0] == (f'{url}{new_resource.__name__}/', )
        assert json_api.app.add_url_rule.call_args[1]['view_func'].__name__ == f'{view}_{new_resource.__name__}'

        json_api.app = None

    def test__create_event_resource__with_blueprint(self):
        json_api.blueprint = mock.Mock()
        json_api.blueprint.name = 'some_blueprint'
        view, url = 'some_resource', '/some_resource/'
        event_plugin._create_event_resource(base_resource=SomeResourceList,
                                            event=OkEvents.event_ok,
                                            method='POST',
                                            view=view,
                                            urls=[url],
                                            self_json_api=json_api)
        assert len(json_api.resource_registry) == 2
        new_resource = json_api.resource_registry[-1]
        assert new_resource.view == f'{json_api.blueprint.name}.{view}'
        self._check_new_resource(new_resource)

        assert len(json_api.resources) == 1  # shouldn't write to resources if app provided
        json_api.blueprint.add_url_rule.assert_called_once()
        assert json_api.blueprint.add_url_rule.call_args[0] == (f'{url}{new_resource.__name__}/', )
        assert json_api.blueprint.add_url_rule.call_args[1]['view_func'].__name__ == f'{view}_{new_resource.__name__}'

        json_api.blueprint = None

    @mock.patch.object(EventPlugin, '_create_event_resource')
    def test_before_route__no_events(self, mock__create_event_resource):
        view, urls = 'some_resource', ['/some_resource/']
        event_plugin.before_route(SomeResourceList, view, urls, json_api)
        mock__create_event_resource.assert_not_called()

    @mock.patch.object(EventPlugin, '_create_event_resource')
    def test_before_route__with_events(self, mock__create_event_resource):
        view, urls = 'some_resource', ['/some_resource/']
        SomeResourceList.events = OkEvents
        expected_events_and_methods = list(event_plugin._events_with_methods(OkEvents))

        event_plugin.before_route(SomeResourceList, view, urls, json_api)
        assert mock__create_event_resource.call_count == 2
        for i, (args, _) in enumerate(mock__create_event_resource.call_args_list):
            assert args == (SomeResourceList, *expected_events_and_methods[i], view, urls, json_api)
