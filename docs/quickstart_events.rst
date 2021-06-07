.. _quickstart_events:

Events Example
--------------

EventPlugin example for Flask-COMBO-JSONAPI API with ComboJSONAPI:

.. literalinclude:: ../examples/api_events.py
    :language: python

.. warning::

    In this example Flask-SQLAlchemy is used, so you'll need to install it before running this example.

    $ pip install flask_sqlalchemy

Save `this file <https://github.com/AdCombo/combojsonapi/blob/master/examples/api.py>`_ as api.py and run it using your Python interpreter. Note that we've enabled
`Flask debugging <https://flask.palletsprojects.com/en/2.0.x/quickstart/#debug-mode>`_ mode to provide code reloading and better error
messages. ::

    $ python api.py
     * Running on http://127.0.0.1:5000/
     * Restarting with reloader

.. warning::

    Debug mode should never be used in a production environment!

Classical CRUD operations
-------------------------

Create user object
~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/api_events__create_user
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_events__create_user_result
  :language: HTTP



Get custom event info
~~~~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/api_events__get_custom_info
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_events__get_custom_info_result
  :language: HTTP



Post custom event info
~~~~~~~~~~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/api_events__post_custom_info
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api_events__post_custom_info_result
  :language: HTTP

