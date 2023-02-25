Usage
-----

Commands
---------

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

The following example illustrates how to run multiple plugins simultaneously
with various channel configurations (based on ``pcap`` from ``nxscli-mpl``):

.. code-block:: bash

   python -m nxscli dummy chan 1,2,3,4 pcap --chan 1 100 pcap --chan 2,3 200 pcap 300


Interace commands
=================

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

Configuratio commands
=====================

Available configuration commands:

* ``chan`` - channels declaration and configuration.

  Mandatory if selected plugins require declared channels.

  In the default, all channels from this command are passed to the plugins.
  This behaviour can be surpassed with the plugin option ``--chan``.

* ``trig`` - softwar triggers configuration.

  Optional, at default all channels are always-on.

  Triggers can be configured per channel with the option ``--trig``.


Plugin commands
===============

Plugins supported so far:

* ``pcsv`` - store samples in CSV files
* ``pdevinfo`` - show information about the connected NxScope device
* ``pnone`` - capture data and do nothing with them
* ``pprinter`` - capture data and print samples

For more information, use the plugin's ``--help`` option.
