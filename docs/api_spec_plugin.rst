.. _api_spec_plugin:

ApiSpec plugin
--------------

Plugin **ApiSpecPlugin** adds the following features:

1. Auto-generated documentation for JSON API, **ResourceList** and **ResourceDetail** resource managers.
2. Support for auto-generating documentation of RPC API made with :ref:`EventPlugin <event_plugin>`
3. Tag-based API grouping in **swagger**.

Plugin is based on **apispec** using :ref:`RestfulPlugin <restful_plugin>`.

How to use
~~~~~~~~~~
To start, do the following:

1. Add a plugin instance at application initialization.
2. Plugin supports the following parameters:

    * :code:`app: Flask` - application instance
    * :code:`decorators: Tuple = None` - tuple with decorators which will get attached to **swagger**
    * :code:`tags: Dict[str, str] = None` - list of tags with descriptions; routers can be grouped by these tags.

3. When declaring routers, you can specify a tag :code:`tag: str`. Tag should be listed at plugin initialization, or you'll get an error.
4. When adding a RPC API view made with :ref:`EventPlugin <event_plugin>`, describe the API using yaml in the view beginning
   `API description structure <https://swagger.io/docs/specification/data-models/>`_.

Plugin usage example is available :ref:`in EventPlugin description <event_plugin>`.
