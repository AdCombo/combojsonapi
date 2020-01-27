ComboJSONAPI
============
ComboJSONAPI is a set of plugins made for `Flask-JSONAPI <https://github.com/AdCombo/flask-jsonapi>`_ module.

1. **Permission** plugin enables access control to models and their fields in GET, POST,
   PATCH and DELETE methods. (`Permission plugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/permission_plugin.rst>`_)
2. **ApiSpecPlugin** simplifies automated JSONAPI documentation.
   JSONAPI (`ApiSpecPlugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/api_spec_plugin.rst>`_)
3. **RestfulPlugin** for apispec library in the **ApiSpecPlugin** enables documenting GET parameters
   with Marshmallow schemes. (`RestfulPlugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/restful_plugin.rst>`_)
4. **EventPlugin** enables RPC creation for those cases when you can't make it with pure JSON:API
   (`EventPlugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/event_plugin.rst>`_).
5. **PostgreSqlJSONB** features filtering and sorting data by first-level key values of JSONB values in
   PostgreSQL (`PostgreSqlJSONB docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/postgresql_jsonb.rst>`_).

Installation
============

:code:`pip install https://github.com/AdCombo/combojsonapi.git`


Contributing
============
If you want to contribute to the code or documentation, the `Contributing guide is the best place to start`_.
If you have questions, feel free to ask


License
=======
`MIT`_

.. _`Contributing guide is the best place to start`: https://github.com/AdCombo/combojsonapi/blob/master/CONTRIBUTING.rst
.. _`MIT`: https://github.com/AdCombo/combojsonapi/blob/master/LICENSE