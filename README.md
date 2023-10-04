# Nxscli
![master workflow](https://github.com/railab/nxscli/actions/workflows/master.yml/badge.svg)

Nxscli is a command-line client package for the [Apache NuttX](https://nuttx.apache.org/)
NxScope real-time logging module.

Compatible with Python 3.10+.

## Features

* Plugins architecture, extendable through ``nxscli.extensions`` entrypoint
* Client-based triggering (global and per-channel triggers)
* Save data to CSV files
* Print samples
* Stream data over UDP (compatible with [PlotJuggler](https://github.com/facontidavide/PlotJuggler))
* NxScope protocol via serial port or Segger RTT interface

## Features Planned

* More triggering types
* Boolean operations on triggers
* Virtual channels and math operations on channels data
* Improve `pdevinfo` output (human-readable prints)
* Interactive mode

## Plugins

By default, we only support features that depend on the standard Python libraries.
The functionality is expadned by installing plugins.
Plugins are automatically deteceted by Nxscli.

Available plugins:

* [nxscli-mpl](https://github.com/railab/nxscli-mpl) - Matplotlib extension
* [nxscli-np](https://github.com/railab/nxscli-np) - Numpy extension

## Plugins Planned

* Stream data as audio (inspired by audio knock detection systems)
* PyQtGraph support

## Instalation

Nxscli can be installed by running `pip install nxscli`.

To install latest development version, use:

`pip install git+https://github.com/railab/nxscli.git`

## Usage

Look at [docs/usage](docs/usage.rst).


## Contributing

All contributions are welcome to this project. 

To get started with developing Nxscli, see [CONTRIBUTING.md](CONTRIBUTING.md).

