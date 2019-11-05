ComboJSONAPI - это набор плагинов для библиотеки `Flask-REST-JSONAPI <https://flask-rest-jsonapi.readthedocs.io/en/latest/quickstart.html>`_
============================================================================================================================================
1. Плагин **Permission** позволяющий создавать различные системы доступа к моделям и полям на выгрузку/создание/изменение/удаление (`Документация для Permission <docs/permission_plugin.rst>`_)
2. Плагин **ApiSpecPlugin** позволяющий генерировать упрощённую автодокументацию для JSONAPI (`Документация для ApiSpecPlugin <docs/api_spec_plugin.rst>`_)
3. Плагин **RestfulPlugin** для библиотеки apispec внутри плагина **ApiSpecPlugin** способствующий описанию параметров в get запросах при помощью схем marshmallow (`Документация для RestfulPlugin <docs/restful_plugin.rst>`_)
4. Плагин **EventPlugin** для создания RPC, для тех случаев когда очень тяжело обойтись только JSON:API (`Документация для EventPlugin <docs/event_plugin.rst>`_).
5. Плагин **PostgreSqlJSONB** для возможности фильтровать и сортировать по верхним ключам в полях `JSONB`:code:\ в PostgreSQL (`Документация для PostgreSqlJSONB <docs/postgresql_jsonb.rst>`_).

Want to contribute?
===================
If you want to contribute through code or documentation, the `Contributing guide is the best place to start`_.
If you have questions, feel free to ask

.. _`Contributing guide is the best place to start`: https://github.com/AdCombo/ComboJSONAPI/CONTRIBUTING.rst
