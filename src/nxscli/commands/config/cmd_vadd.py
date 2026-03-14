"""Virtual channel declaration command."""

from typing import TYPE_CHECKING

import click

from nxscli.channelref import ChannelRef
from nxscli.cli.environment import Environment, pass_environment
from nxscli.cli.types import StringList
from nxscli.virtual.services import get_runtime

if TYPE_CHECKING:
    from nxscli.phandler import PluginHandler


def _get_phandler(ctx: Environment) -> "PluginHandler":
    assert ctx.phandler is not None
    return ctx.phandler


def _parse_param_value(raw: str) -> object:
    low = raw.lower()
    if low in ("true", "false"):
        return low == "true"
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except ValueError:
        return raw


def _parse_params(params: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for token in params:
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            raise click.BadParameter(f"Invalid param token: {token}")
        key, raw = token.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if not key:
            raise click.BadParameter("Parameter key must not be empty")
        parsed[key] = _parse_param_value(raw)
    return parsed


def _merge_required_sources(ctx: Environment, inputs: list[str]) -> None:
    """Ensure physical virtual-input sources are configured for streaming."""
    required: list[ChannelRef] = []
    for token in inputs:
        tok = token.strip()
        if tok.isnumeric():
            required.append(ChannelRef.physical(int(tok)))

    if not required:
        return

    if ctx.channels is None:
        ctx.channels = (required, 0)
        return

    channels, divider = ctx.channels
    if any(ref.is_all for ref in channels):
        return

    merged = list(channels)
    for ref in required:
        if ref not in merged:
            merged.append(ref)
    ctx.channels = (merged, divider)


@click.command(name="vadd")
@click.argument("channel_id", type=int)
@click.argument("inputs", type=StringList())
@click.option("--name", type=str, default=None)
@click.option(
    "--operator",
    type=click.Choice(
        [
            "scale_offset",
            "math_binary",
            "stats_running",
        ]
    ),
    default="scale_offset",
)
@click.option(
    "--params",
    type=StringList(),
    default="",
    help="Operator params in key=value format, comma separated",
)
@pass_environment
def cmd_vadd(
    ctx: Environment,
    channel_id: int,
    name: str | None,
    operator: str,
    inputs: list[str],
    params: list[str],
) -> bool:
    """[config] Add virtual channel to shared runtime."""
    _merge_required_sources(ctx, inputs)
    runtime = get_runtime(_get_phandler(ctx))
    parsed_params = _parse_params(params)
    aliases = runtime.add_virtual_channel(
        channel_id=channel_id,
        name=name or f"virt{channel_id}",
        operator=operator,
        inputs=tuple(inputs),
        params=parsed_params,
    )
    for alias, output_id in aliases:
        click.echo(f"virtual output {output_id} -> channel {alias}")
    return True
