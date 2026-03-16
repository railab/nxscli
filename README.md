# Nxscli
![master workflow](https://github.com/railab/nxscli/actions/workflows/master.yml/badge.svg)

Nxscli is a command-line client package for the [Apache NuttX](https://nuttx.apache.org/)
NxScope real-time logging module.

It is also a reusable Python runtime layer for NxScope streaming, channel
control, triggers, and plugin orchestration. The `nxscli` internals are used
by other tools (for example GUI applications) to build more advanced workflows
without re-implementing NxScope communication logic.

Compatible with Python 3.10+.

## Features

* Plugins architecture, extendable through ``nxscli.extensions`` entrypoint
* Client-based triggering (global and per-channel triggers)
* Save data to CSV files
* Save data to Numpy files (`pnpsave`) and memmap files (`pnpmem`)
* Print samples
* Stream data over UDP (compatible with [PlotJuggler](https://github.com/facontidavide/PlotJuggler))
* NxScope protocol via serial port or Segger RTT interface
* Virtual channels and math operations on channels data
* Optional control server (`--control-server`) for extentions

## Features Planned

* More triggering types
* Boolean operations on triggers
* Improve `pdevinfo` output (human-readable prints)
* Interactive mode

## Plugins

By default, `nxscli` ships with core plugins including CSV, printer, UDP,
and NumPy file capture (`pnpsave` and `pnpmem`).
Additional functionality is expanded by installing optional plugins.
Plugins are automatically detected by Nxscli.

Available plugins:

* [nxscli-mpl](https://github.com/railab/nxscli-mpl) - Matplotlib extension

## Plugins Planned

* Stream data as audio (inspired by audio knock detection systems)
* PyQtGraph support

## Instalation

Nxscli can be installed by running `pip install nxscli`.

To install latest development version, use:

`pip install git+https://github.com/railab/nxscli.git`

## Usage

Look at [docs/usage](docs/usage.rst).

## Reuse as a Library

`nxscli` is not only a CLI frontend. It can be imported and reused by external
applications that need:

* NxScope connection handling (serial/RTT and compatible interfaces)
* channel configuration and stream lifecycle control
* plugin loading and runtime execution
* trigger and data-processing orchestration

This makes `nxscli` the integration layer for higher-level tools such as
custom dashboards, GUIs, and automation scripts.


## Contributing

All contributions are welcome to this project. 

To get started with developing Nxscli, see [CONTRIBUTING.md](CONTRIBUTING.md).
