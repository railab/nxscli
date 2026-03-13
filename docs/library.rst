Using Nxscli as a Library
-------------------------

Nxscli is not only a CLI frontend. It can also be reused as a Python
integration layer for higher-level tools such as GUIs, dashboards, and
automation scripts.

Typical reusable components include:

* NxScope connection and interface handling
* channel configuration and stream lifecycle control
* plugin loading and runtime orchestration
* trigger and data-processing integration

Minimal example
===============

.. code-block:: python

   from nxscli.plugins_loader import plugins_list
   from nxscli.phandler import PluginHandler
   from nxslib.intf.dummy import DummyDev
   from nxslib.proto.parse import Parser
   from nxslib.nxscope import NxscopeHandler

   intf = DummyDev()
   parse = Parser()

   with NxscopeHandler(intf, parse) as nxscope:
       with PluginHandler(plugins_list) as phandler:
           phandler.nxscope_connect(nxscope)

           # Configure and run as needed by your application:
           nxscope.ch_enable([0], writenow=True)
           nxscope.stream_start()
           pid = phandler.plugin_start_dynamic("pprinter", channels=[0])

           # ... do work ...

           phandler.plugin_stop_dynamic(pid)
           nxscope.stream_stop()
       # phandler.cleanup() called automatically on exit
   # nxscope.disconnect() called automatically on exit

