Changelog
*********

**0.1.1**
=========

Enhancements
============

* Added parameter **strict** in PermissionPlugin #- `@Znbiz`_
* Added parameter **trailing_slash** in EventPlugin #- `@Znbiz`_
* English docs #- `@Yakov Shapovalov`_
* Update marshmallow -> 3.0.1 #- `@Znbiz`_

Bug Fixes
=========

* update Relationship #- `@Znbiz`_
* Constant splitter for filters, sorts and includes in plugin `PostgreSqlJSONB`_ #- `@Znbiz`_
* Fix resource.schema == None in plugin `ApiSpecPlugin`_ #- `@Znbiz`_
* Fix sorting in plugin `PostgreSqlJSONB`_ #- `@Znbiz`_
* Improved model fields check for options(load_only) in `Permission`_ #- `@Znbiz`_
* Implement disable_global_decorators, minor refactor and upgrade events, update docs in plugin
  `EventPlugin`_  #- `@Suren Khorenyan`_
* typo permission_for_path -> permission_for_patch and create get_decorators_for_resource
  in plugin `Permission`_ #- `@Suren Khorenyan`_
* Create status util #- `@Suren Khorenyan`_
* Refactor api spec params for get in plugin `ApiSpecPlugin`_ #- `@Suren Khorenyan`_
* Fix permission plugin initialization #- `@Suren Khorenyan`_
* Constant splitter for filters, sorts and includes #- `@Suren Khorenyan`_
* Configure setup, update .gitignore #- `@Suren Khorenyan`_

**0.1.0**
=========

Enhancements
============

* Created plugin `Permission`_ for flask-rest-jsonapi #- `@Znbiz`_
* Created plugin `ApiSpecPlugin`_ for flask-rest-jsonapi #- `@Znbiz`_
* Created plugin `EventPlugin`_ for flask-rest-jsonapi #- `@Znbiz`_
* Created plugin `PostgreSqlJSONB`_ for flask-rest-jsonapi #- `@Znbiz`_
* Created plugin `RestfulPlugin`_ for ApiSpec #- `@Znbiz`_


.. _`RestfulPlugin`: https://github.com/AdCombo/ComboJSONAPI/docs/restful_plugin.rst
.. _`PostgreSqlJSONB`: https://github.com/AdCombo/ComboJSONAPI/docs/postgresql_jsonb.rst
.. _`EventPlugin`: https://github.com/AdCombo/ComboJSONAPI/docs/event_plugin.rst
.. _`ApiSpecPlugin`: https://github.com/AdCombo/ComboJSONAPI/docs/api_spec_plugin.rst
.. _`Permission`: https://github.com/AdCombo/ComboJSONAPI/docs/permission_plugin.rst

.. _`@Suren Khorenyan`: https://github.com/mahenzon
.. _`@Znbiz`: https://github.com/znbiz
.. _`@Yakov Shapovalov`: https://github.com/photovirus