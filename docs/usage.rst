Usage
-----

You can run _Nxscli_ as a package: 

.. code-block:: bash
   python -m nxscli [interface] [config] [plugins]

Only one [interface] can be selected but many [config] and [plugins] commands can be handled when calling the program.
[config] commands are global for all plugins, but each plugin can overwritte this with dedicated options.

Plugins will be launched in parallel.

For commands details use `--help` option.

To run the application with a simulated mode use this command:

.. code-block:: bash
   python -m nxscli dummy [config] [plugins]

Example 1: 

.. code-block:: bash
   python -m nxscli dummy chan 1,2,3,4 pcap --chan 1 100 pcap --chan 2,3 200 pcap 300

NuttX simulation
----------------

You can establish a connection with the simulated NuttX target using `socat`:


.. code-block:: bash
   SERIAL_HOST={PATH}/ttyNX0
   SERIAL_NUTTX={PATH}/ttySIM0

   socat PTY,link=$SERIAL_NUTTX PTY,link=$SERIAL_HOST &
   stty -F $SERIAL_NUTTX raw
   stty -F $SERIAL_HOST raw
   stty -F $SERIAL_NUTTX 115200
   stty -F $SERIAL_HOST 115200
