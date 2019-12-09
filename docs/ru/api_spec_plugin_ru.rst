Плагин ApiSpecPlugin (`EN`_ | `RU`_)
--------------------------------------

Плагин **ApiSpecPlugin** добавляет:

1. Автоматически генерирующуюся документацию для JSONAPI, для ресурс менеджеров **ResourceList** и **ResourceDetail**
2. Поддержка генерации документации для RPC API созданного с помощью плагина `EventPlugin <docs/ru/event_plugin.rst>`_
3. Группировка созданного API по тегам (в **swagger**).

Плагин построен поверх **apispec** с подключением плагина `RestfulPlugin <docs/ru/restful_plugin.rst>`_.

Краткий алгоритм работы плагина: **apispec** -> **swagger**

Работа с плагином
~~~~~~~~~~~~~~~~~
Чтобы начать работать с плагином, нужно:

1. При инициализации приложения добавляем инстанс плагина.
2. При инициализации плагина, принимаются следующие параметры:

    * :code:`app: Flask` - истанс приложения
    * :code:`decorators: Tuple = None` - кортеж с декораторами, которые повесятся на роутер **swagger**
    * :code:`tags: Dict[str, str] = None` - список тегов с их описанием, они потом применяются при
      группирование роутеров в группы по тегам.

3. При объявлении роутеров, добавляется параметр :code:`tag: str` если здесь указать тег, который не описан
   при инициализации плагина, то выскочит ошибка.
4. Если добавляем view RPC API использую плагин `EventPlugin <docs/ru/event_plugin.rst>`_, то в начале view
   описываем API используя yaml `структура описания API <https://swagger.io/docs/specification/data-models/>`_.

Пример работы с плагином можно посмотреть в примере у плагина EventPlugin `тут <docs/ru/event_plugin.rst>`_.

.. _`EN`: https://github.com/AdCombo/ComboJSONAPI/docs/en/api_spec_plugin.rst
.. _`RU`: https://github.com/AdCombo/ComboJSONAPI/docs/ru/api_spec_plugin.rst
