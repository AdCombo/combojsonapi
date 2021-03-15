Changelog
*********


**1.1.0**
=========

Enhancements
============

* Upgrade apispec, fix tests `#33`_ #- `@mahenzon`_
* provide custom event params via `extra` attribute `#34`_ #- `@mahenzon`_
* build and localize docs for RTD `#36`_ #- `@mahenzon`_
* Add case for permission methods in docs `#30`_ #- `@Bykov25`_


**1.0.5**
=========

Bug Fixes
=========

* Distribute apispec templates #- `@mahenzon`_


**1.0.3**
=========

Enhancements
============

* Add custom marshmallow fields for PostgreSQL filtering (PostgreSqlJSONB plugin) #- `@Znbiz`_
* Filtering and sorting nested JSONB fields (PostgreSqlJSONB plugin) #- `@tarasovdg1`_


**1.0.0**
=========

Changes
=======

* Rename Flask-REST-JSONAPI to Flask-COMBO-JSONAPI #- `@mahenzon`_


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
  `EventPlugin`_  #- `@mahenzon`_
* typo permission_for_path -> permission_for_patch and create get_decorators_for_resource
  in plugin `Permission`_ #- `@mahenzon`_
* Create status util #- `@mahenzon`_
* Refactor api spec params for get in plugin `ApiSpecPlugin`_ #- `@mahenzon`_
* Fix permission plugin initialization #- `@mahenzon`_
* Constant splitter for filters, sorts and includes #- `@mahenzon`_
* Configure setup, update .gitignore #- `@mahenzon`_

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

.. _`@mahenzon`: https://github.com/mahenzon
.. _`@Znbiz`: https://github.com/znbiz
.. _`@Yakov Shapovalov`: https://github.com/photovirus
.. _`@tarasovdg1`: https://github.com/tarasovdg1
.. _`@Bykov25`: https://github.com/Bykov25

.. _`#30`: https://github.com/AdCombo/combojsonapi/pull/30
.. _`#33`: https://github.com/AdCombo/combojsonapi/pull/33
.. _`#34`: https://github.com/AdCombo/combojsonapi/pull/34
.. _`#36`: https://github.com/AdCombo/combojsonapi/pull/36
