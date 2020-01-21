ComboJSONAPI
============
ComboJSONAPI is a set of plugins made for `Flask-REST-JSONAPI <https://flask-rest-jsonapi.readthedocs.io/en/latest/quickstart.html>`_ module.

1. **Permission** plugin enables access control to models and their fields in GET, POST, PATCH and DELETE methods. (`Permission plugin docs <docs/permission_plugin.rst>`_)
2. **ApiSpecPlugin** simplifies automated JSONAPI documentation.
   JSONAPI (`ApiSpecPlugin docs <docs/api_spec_plugin.rst>`_)
3. **RestfulPlugin** for apispec library in the **ApiSpecPlugin** enables documenting GET parameters with Marshmallow schemes. (`RestfulPlugin docs <docs/restful_plugin.rst>`_)
4. **EventPlugin** enables RPC creation for those cases when you can't make it with pure JSON:API (`EventPlugin docs <docs/event_plugin.rst>`_).
5. **PostgreSqlJSONB** features filtering and sorting data by first-level key values of JSONB values in PostgreSQL (`PostgreSqlJSONB docs <docs/postgresql_jsonb.rst>`_).

Installation
============

:code:`pip install git+ssh://git@github.com/AdCombo/ComboJSONAPI.git`


Contributing
============
If you want to contribute to the code or documentation, the `Contributing guide is the best place to start`_.
If you have questions, feel free to ask


License
=======
`MIT`_

.. _`Contributing guide is the best place to start`: https://github.com/AdCombo/ComboJSONAPI/CONTRIBUTING.rst
.. _`MIT`: https://github.com/AdCombo/ComboJSONAPI/LICENSE