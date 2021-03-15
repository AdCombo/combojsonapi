.. image:: https://github.com/AdCombo/combojsonapi/workflows/Python%20tests%20and%20coverage/badge.svg
   :alt: ComboJSONAPI actions
   :target: https://github.com/AdCombo/combojsonapi/actions

.. image:: https://coveralls.io/repos/github/AdCombo/combojsonapi/badge.svg?branch=master
   :alt: ComboJSONAPI coverage
   :target: https://coveralls.io/github/AdCombo/combojsonapi?branch=master

.. image:: https://img.shields.io/pypi/v/combojsonapi.svg
   :alt: PyPI
   :target: http://pypi.org/p/combojsonapi

ComboJSONAPI
============
ComboJSONAPI is a set of plugins made for `Flask-COMBO-JSONAPI <https://github.com/AdCombo/flask-combo-jsonapi>`_ module.

1. **Permission** plugin enables access control to models and their fields in GET, POST,
   PATCH and DELETE methods. (`Permission Plugin docs`_)
2. **ApiSpecPlugin** simplifies automated JSONAPI documentation. (`ApiSpec Plugin docs`_)
3. **RestfulPlugin** for apispec library in the **ApiSpecPlugin** enables documenting GET parameters
   with Marshmallow schemas. (`Restful Plugin docs`_)
4. **EventPlugin** enables RPC creation for those cases when you can't make it with pure JSON:API
   (`Event Plugin docs`_).
5. **PostgreSqlJSONB** features filtering and sorting data by first-level key values of JSONB values in
   PostgreSQL (`PostgreSqlJSONB Plugin docs`_).

Installation
============

:code:`pip install combojsonapi`

Documentation
=============

- https://combojsonapi.readthedocs.io/


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


- add new langs via additional flag :code:`-l es`
- add translations to :code:`docs/locale/<lang>/LC_MESSAGES`
- to check your translations run :code:`sphinx-build -b html -D language=ru . _build/html/ru` and check generated HTML files


License
=======
`MIT`_

.. _`Contributing guide is the best place to start`: https://github.com/AdCombo/combojsonapi/blob/master/CONTRIBUTING.rst
.. _`MIT`: https://github.com/AdCombo/combojsonapi/blob/master/LICENSE

.. _`Event Plugin docs`: https://combojsonapi.readthedocs.io/en/latest/event_plugin.html
.. _`ApiSpec Plugin docs`: https://combojsonapi.readthedocs.io/en/latest/api_spec_plugin.html
.. _`Restful Plugin docs`: https://combojsonapi.readthedocs.io/en/latest/restful_plugin.html
.. _`Permission Plugin docs`: https://combojsonapi.readthedocs.io/en/latest/permission_plugin.html
.. _`PostgreSqlJSONB Plugin docs`: https://combojsonapi.readthedocs.io/en/latest/postgresql_jsonb_plugin.html
