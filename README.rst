.. image:: https://github.com/AdCombo/combojsonapi/workflows/Python%20tests%20and%20coverage/badge.svg
   :alt: ComboJSONAPI actions
   :target: https://github.com/AdCombo/combojsonapi/actions

.. image:: https://coveralls.io/repos/github/AdCombo/combojsonapi/badge.svg?branch=master
   :alt: ComboJSONAPI coverage
   :target: https://coveralls.io/github/AdCombo/combojsonapi?branch=master

ComboJSONAPI
============
ComboJSONAPI is a set of plugins made for `Flask-COMBO-JSONAPI <https://github.com/AdCombo/flask-combo-jsonapi>`_ module.

1. **Permission** plugin enables access control to models and their fields in GET, POST,
   PATCH and DELETE methods. (`Permission plugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/permission_plugin.rst>`_)
2. **ApiSpecPlugin** simplifies automated JSONAPI documentation. (`ApiSpecPlugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/api_spec_plugin.rst>`_)
3. **RestfulPlugin** for apispec library in the **ApiSpecPlugin** enables documenting GET parameters
   with Marshmallow schemas. (`RestfulPlugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/restful_plugin.rst>`_)
4. **EventPlugin** enables RPC creation for those cases when you can't make it with pure JSON:API
   (`EventPlugin docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/event_plugin.rst>`_).
5. **PostgreSqlJSONB** features filtering and sorting data by first-level key values of JSONB values in
   PostgreSQL (`PostgreSqlJSONB docs <https://github.com/AdCombo/combojsonapi/blob/master/docs/en/postgresql_jsonb.rst>`_).

Installation
============

:code:`pip install combojsonapi`


Contributing
============
If you want to contribute to the code or documentation, the `Contributing guide is the best place to start`_.
If you have questions, feel free to ask


Documentation
=============

To update docs:


.. code:: sh

    # go to docs dir
    cd docs
    # gen .pot files
    make gettext
    # update .po files for existing langs / create new
    sphinx-intl update -p _build/locale -l ru


- add new langs via additional flag "-l es"
- add translations to :code:`docs/locale/<lang>/LC_MESSAGES`
- to check your translations run :code:`sphinx-build -b html -D language=ru . _build/html/ru` and check generated HTML files


License
=======
`MIT`_

.. _`Contributing guide is the best place to start`: https://github.com/AdCombo/combojsonapi/blob/master/CONTRIBUTING.rst
.. _`MIT`: https://github.com/AdCombo/combojsonapi/blob/master/LICENSE
