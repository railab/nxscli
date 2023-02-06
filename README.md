# Nxscli

_Nxscli_ is the command-line application to the [Apache NuttX](https://nuttx.apache.org/) _NxScope_ real-time logging library.
It is based on [Nxslib](https://github.com/railab/nxslib/) and is entirely written in Python.

## Features

- built-in simulated _NxScope_ device that allows application development without connecting a real NuttX device
- support for the _NxScope_ serial protocol
- dump stream data to CSV files
- plotting with [Matplotlib](https://github.com/matplotlib/matplotlib)
- capture data on a static plot
- real-time animation plot (can be written as `gif` or `mp4` file)

## Contributing

### Setting up for development

Create a new venv and activate it

```
virtualenv venv
. venv/bin/activate
```

install _Nxscli_ in editable mode

`pip install -e .`

and now you are ready to modify the code.

You can run `tox` to verify your changes.
All available environments for tox can be found with

`tox list`

and then run with

`tox -e test`

## Instalation

To install _Nxscli_ locally from this repository use:

`pip install --user .`

## Usage

You can run _Nxscli_ as a package: 

`python -m nxscli [interface] [config] [plugins]`

To run the application with a simulated mode use this command:

`python -m nxscli dummy [config] [plugins]`

Example 1: 

`python -m nxscli dummy chan 1,2,3,4 pcapture --chan 1 100 pcapture --chan 2,3 200 pcapture 300`
