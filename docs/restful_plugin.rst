.. _restful_plugin:

Restful plugin
--------------

**RestfulPlugin** is designed to work with **apispec**, which is used in **ApiSpecPlugin**.

Plugin **RestfulPlugin**:

- it generates views documentation based on API yaml description
- its main purpose is to describe RPC API made with **EventPlugin**.

Plugin usage example is available :ref:`in EventPlugin description <event_plugin>`.
In that example a RPC API view documentation is being parsed via RestfulPlugin
and passed to **apispec** for export into **swagger**.
