.. _quickstart:

Example
-------

An example of Flask-COMBO-JSONAPI API with ComboJSONAPI looks like this:

.. literalinclude:: ../examples/api.py
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

Create object
~~~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/api__create_person
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api__create_person_result
  :language: HTTP


Get object
~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/api__get_person
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api__get_person_result
  :language: HTTP


Get objects
~~~~~~~~~~~

Request:

.. literalinclude:: ./http_snippets/snippets/api__get_persons
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api__get_persons_result
  :language: HTTP


Sparse fields
~~~~~~~~~~~~~

Note that we tell SQLAlchemy that :code:`full_name` requires :code:`first_name` and :code:`first_name` fields.
If we don't declare this dependency in model's :code:`Meta.required_fields`,
when serialising each model will fire two queries to DB to get these fields.

It happens because PermissionPlugin removes not requested fields from
the SQL query for the sake of performance. And :code:`Meta.required_fields`
will tell PermissionPlugin which fields have to be loaded
even if not requested directly.

Request:

.. literalinclude:: ./http_snippets/snippets/api__get_persons__sparse_fields
  :language: HTTP

Response:

.. literalinclude:: ./http_snippets/snippets/api__get_persons__sparse_fields_result
  :language: HTTP

