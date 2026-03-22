"""Version command."""

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, distributions, version

import click


@dataclass(frozen=True)
class PluginPackageVersion:
    """Installed plugin package version details."""

    name: str
    version: str


def _get_package_version(name: str) -> str:
    """Return installed package version or a readable fallback."""
    try:
        return version(name)
    except PackageNotFoundError:
        return "not installed"


def get_plugin_package_versions() -> list[PluginPackageVersion]:
    """Get versions for external nxscli plugin packages."""
    packages: dict[str, PluginPackageVersion] = {}

    for dist in distributions():
        entry_points = [
            entry
            for entry in dist.entry_points
            if entry.group == "nxscli.extensions"
        ]
        if not entry_points:
            continue

        name = dist.metadata["Name"]
        if name == "nxscli":
            continue

        packages[name] = PluginPackageVersion(
            name=name,
            version=dist.version,
        )

    return sorted(packages.values(), key=lambda item: item.name)


@click.command(name="version")
def cmd_version() -> None:
    """Print installed versions for nxscli, nxslib and plugin packages."""
    click.echo(f"nxscli: {_get_package_version('nxscli')}")
    click.echo(f"nxslib: {_get_package_version('nxslib')}")
    click.echo("plugins:")

    for package in get_plugin_package_versions():
        click.echo(f"- {package.name}: {package.version}")
