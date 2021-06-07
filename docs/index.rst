=========================================================================
ComboJSONAPI: Plugins to improve functionality of the Flask-COMBO-JSONAPI
=========================================================================

.. image:: https://github.com/AdCombo/combojsonapi/workflows/Python%20tests%20and%20coverage/badge.svg
   :alt: ComboJSONAPI actions
   :target: https://github.com/AdCombo/combojsonapi/actions

.. image:: https://coveralls.io/repos/github/AdCombo/combojsonapi/badge.svg?branch=master
   :alt: ComboJSONAPI coverage
   :target: https://coveralls.io/github/AdCombo/combojsonapi?branch=master

.. image:: https://img.shields.io/pypi/v/combojsonapi.svg
   :alt: PyPI
   :target: http://pypi.org/p/combojsonapi

.. module:: flask_combo_jsonapi


``ComboJSONAPI`` is a set of plugins made for Flask-COMBO-JSONAPI_.

.. _Flask-COMBO-JSONAPI: https://flask-combo-jsonapi.readthedocs.io/

1. **Permission** plugin enables access control to models
   and their fields in GET, POST, PATCH and DELETE methods.
2. **ApiSpecPlugin** simplifies automated JSONAPI documentation.
3. **RestfulPlugin** for apispec_ library in the **ApiSpecPlugin** enables documenting GET parameters with Marshmallow schemas.
4. **EventPlugin** enables RPC creation for those cases when you can't make it with pure JSON:API.
5. **PostgreSqlJSONB** features filtering and sorting data by first-level key values of JSONB values in PostgreSQL.

.. _apispec: https://apispec.readthedocs.io/


Contents
========

.. toctree::

   installation
   quickstart
   quickstart_events
   event_plugin
   permission_plugin
   api_spec_plugin
   restful_plugin
   postgresql_jsonb_plugin
   using_plugins

.. toctree::
   :maxdepth: 2

   changelog


Documentation
=============

- https://combojsonapi.readthedocs.io/

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
