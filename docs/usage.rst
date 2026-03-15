=====
Usage
=====

Commands
========

You can run Nxscli as a Python module:

.. code-block:: bash

   python -m nxscli [interface] [config] [plugins]


There are three types of commands:

1. ``interface`` - select communication interface
2. ``config`` - set global configuration
3. ``plugins`` - process data from NxScope

You can select many [config] and [plugins] commands at a time.
Plugin-specific options can overwrite some of the global configuration options.
Plugins are launched in parallel, allowing you to process data in multiple ways at
the same time.

For commands details use ``--help`` option.

Global options include:

* ``--control-server`` - enable optional control server plugin
  (disabled by default).
* ``--control-endpoint`` - server endpoint
  (``unix://``, ``unix-abstract://`` or ``tcp://``).

The following example illustrates how to run multiple plugins simultaneously
with various channel configurations (based on ``pcap`` from ``nxscli-mpl``):

.. code-block:: bash

   python -m nxscli dummy chan 1,2,3,4 pcap --chan 1 100 pcap --chan 2,3 200 pcap 300

Library integration guide:

* :doc:`library`

Interface Commands
------------------

Supported interface commands:

* ``dummy`` - select simulated NxScope interface

  Available device channels:

  - chan0 - vdim = 1, random()
  - chan1 - vdim = 1, saw wave
  - chan2 - vdim = 1, triangle wave
  - chan3 - vdim = 2, random()
  - chan4 - vdim = 3, random()
  - chan5 - vdim = 3, static vector = [1.0, 0.0, -1.0]
  - chan6 - vdim = 1, 'hello' string
  - chan7 - vdim = 3, static vector = [1.0, 0.0, -1.0], meta = 1B int
  - chan8 - vdim = 0, meta = 'hello string', mlen = 16
  - chan9 - vdim = 3, 3-phase sine wave

* ``serial`` - select serial port NxScope interface

* ``rtt`` - select Segger RTT as NxScope interface

Configuration Commands
----------------------

Available configuration commands:

* ``chan`` - channels declaration and configuration.

  Mandatory if selected plugins require declared channels.

  In the default, all channels from this command are passed to the plugins.
  This behaviour can be surpassed with the plugin option ``--chan``.

* ``trig`` - softwar triggers configuration.

  Optional, at default all channels are always-on.

  Triggers can be configured per channel with the option ``--trig``.

* ``vadd`` - add virtual channel in `nxscli` virtual runtime.

  This command declares a derived channel from one or more inputs.
  The command is non-interactive and can be chained with plugin commands.
  Use ``--operator`` to select transform and ``--params`` for
  comma-separated ``key=value`` operator arguments.

  Example command form:

  .. code-block:: bash

     python -m nxscli dummy vadd --operator scale_offset --params scale=2,offset=1 100 0 pprinter --chan v100 10

  In command chaining, place command options before positional arguments.
  For virtual data output, select virtual channel explicitly via plugin
  ``--chan vNN`` (for example ``--chan v100``).
  Source physical channels from ``vadd`` inputs are auto-configured.


Plugin Commands
---------------

Plugins supported so far:

* ``pcsv`` - store samples in CSV files
* ``pdevinfo`` - show information about the connected NxScope device
* ``pnone`` - capture data and do nothing with them
* ``pprinter`` - capture data and print samples
* ``pudp`` - stream data over UDP

For more information, use the plugin's ``--help`` option.

Dummy Device Cheatsheet
=======================

Use these commands for quick local testing without hardware.
All examples use the ``dummy`` interface and channel ``0``.

Device info
===========

.. code-block:: bash

   python -m nxscli dummy pdevinfo

Print stream samples
====================

.. code-block:: bash

   python -m nxscli dummy chan 0 pprinter 50

Capture and discard samples
===========================

.. code-block:: bash

   python -m nxscli dummy chan 0 pnone 50000

Store samples to CSV
====================

.. code-block:: bash

   python -m nxscli dummy chan 0 pcsv 200 /tmp/nxscope_csv

Stream samples over UDP
=======================

.. code-block:: bash

   python -m nxscli dummy chan 0 pudp 2000 --address 127.0.0.1 --port 9870

Run multiple plugins in one command
===================================

.. code-block:: bash

   python -m nxscli dummy chan 0 pprinter 20 pcsv 20 /tmp/nxscope_csv pudp 20
