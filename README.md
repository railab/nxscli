# Nxscli
![master workflow](https://github.com/railab/nxscli/actions/workflows/master.yml/badge.svg)

Nxscli is a command-line client package for the [Apache NuttX](https://nuttx.apache.org/)
NxScope real-time logging module.

Compatible with Python 3.10+.

## Features

* Save data to CSV files
* Save data to NumPy files (`.npy`)
* NumPy `numpy.memmap()` support
* Plotting with [Matplotlib](https://github.com/matplotlib/matplotlib),
  * Capture data on a static plot
  * Real-time animation plot (can be written as `gif` or `mp4` file)
* Client-based triggering (global and per-channel triggers)

## Features Planned

* Plugins as Python modules (decoupling from Matplotlib and Numpy dependencies)
* Stream data as audio (inspired by audio knock detection systems)
* More triggering types
* Boolean operations on triggers
* Virtual channels and math operations on channels data
* Improve `pdevinfo` output (human-readable prints)
* Stream metadata as X-axis
* Interactive mode
* Maybe support for PyQtGraph ?

## Instalation

For now, only installation from sources is available.

To install Nxscli locally from this repository use:

`pip install --user git+https://github.com/railab/nxscli.git`

## Usage

Look at [docs/usage](docs/usage.rst).


## Contributing

All contributions are welcome to this project. 

To get started with developing Nxscli, see [CONTRIBUTING.md](CONTRIBUTING.md).

