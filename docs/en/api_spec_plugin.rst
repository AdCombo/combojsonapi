ApiSpecPlugin (`EN`_ | `RU`_)
-----------------------------

Plugin **ApiSpecPlugin** adds the following features:

1. Auto-generated documentation for JSON API, **ResourceList** and **ResourceDetail** resource managers.
2. Support for auto-generating documentation of RPC API made with `EventPlugin <docs/event_plugin.rst>`_
3. Tag-based API grouping in **swagger**.

Plugin is based on **apispec** using `RestfulPlugin <docs/en/restful_plugin.rst>`_.

How to use
~~~~~~~~~~
To start, do the following:

1. Add a plugin instance at application initialization.
2. Plugin supports the following parameters:

    * :code:`app: Flask` - application instance
    * :code:`decorators: Tuple = None` - tuple with decorators which will get attached to **swagger**
    * :code:`tags: Dict[str, str] = None` - list of tags with descriptions; routers can be grouped by these tags.

3. When declaring routers, you can specify a tag :code:`tag: str`. Tag should be listed at plugin initialization, or you'll get an error.
4. When adding a RPC API view made with `EventPlugin <docs/en/event_plugin.rst>`_, describe the API using yaml in the view beginning
   `API description structure <https://swagger.io/docs/specification/data-models/>`_.

Plugin usage sample is available `in EventPlugin description <docs/en/event_plugin.rst>`_.

.. _`EN`: https://github.com/AdCombo/ComboJSONAPI/docs/en/api_spec_plugin.rst
.. _`RU`: https://github.com/AdCombo/ComboJSONAPI/docs/ru/api_spec_plugin.rst
