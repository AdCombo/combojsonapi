Плагинам RestfulPlugin (`EN`_ | `RU`_)
--------------------------------------

Плагин **RestfulPlugin** разработан для **apispec**, который в свою очередь используется в плагине
**ApiSpecPlugin**.

Плагин **RestfulPlugin** позволяет:

1. Генерировать документацию к views на основе документации к view на yaml.
2. Преимущественно плагин разработан для описания RPC API реализованного с помощью плагина **EventPlugin**.

Пример работы с плагином можно посмотреть в описание плагина EventPlugin `тут <https://github.com/AdCombo/combojsonapi/blob/master/docs/ru/event_plugin.rst>`_.
В примере view RPC API документация описана, которая дальше парсится данным плагином и отдаётся в **apispec**
для выгрузки в swagger.

.. _`EN`: https://github.com/AdCombo/combojsonapi/blob/master/docs/en/restful_plugin.rst
.. _`RU`: https://github.com/AdCombo/combojsonapi/blob/master/docs/ru/restful_plugin.rst