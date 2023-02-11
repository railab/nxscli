# Nxscli
![master workflow](https://github.com/railab/nxscli/actions/workflows/master.yml/badge.svg)

_Nxscli_ is a command-line client to the [Apache NuttX](https://nuttx.apache.org/)
_NxScope_ real-time logging module.

Compatible with Python 3.10+.

## Features

* Save data to CSV files
* Save data to NumPy files (`.npy`)
* Plotting with [Matplotlib](https://github.com/matplotlib/matplotlib),
  * Capture data on a static plot
  * Real-time animation plot (can be written as `gif` or `mp4` file)

## Features Planned

* NumPy `numpy.memmap()` support
* Stream data as audio (inspired by audio knock detection systems)
* Client-based triggering (global and per-channel triggers)
* Plugins for character-type channels
* Improve `pdevinfo` output (human-readable prints)
* Metadata as X-axis
* PyQtGraph ??
* Interactive mode ?

## Instalation

To install _Nxscli_ locally from this repository use:

`pip install --user git+https://github.com/railab/nxscli.git`

## Usage

You can run _Nxscli_ as a package: 

`python -m nxscli [interface] [config] [plugins]`

To run the application with a simulated mode use this command:

`python -m nxscli dummy [config] [plugins]`

Example 1: 

`python -m nxscli dummy chan 1,2,3,4 pcap --chan 1 100 pcap --chan 2,3 200 pcap 300`

#### NuttX simulation

You can establish a connection with the simulated NuttX target using `socat`:

```
SERIAL_HOST={PATH}/ttyNX0
SERIAL_NUTTX={PATH}/ttySIM0

socat PTY,link=$SERIAL_NUTTX PTY,link=$SERIAL_HOST &
stty -F $SERIAL_NUTTX raw
stty -F $SERIAL_HOST raw
stty -F $SERIAL_NUTTX 115200
stty -F $SERIAL_HOST 115200
```

## Contributing

#### Setting up for development

1. Clone the repository.

2. Create a new venv and activate it

```
virtualenv venv
. venv/bin/activate
```

3. Install _Nxscli_ in editable mode

`pip install -e .`

and now you are ready to modify the code.

#### CI

Please run `tox` before submitting a patch to be sure your changes will pass CI.
