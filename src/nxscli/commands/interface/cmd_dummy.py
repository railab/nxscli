"""Module containint the dummy interface command for CLI."""

import click
from nxslib.intf.dummy import DummyDev
from nxslib.nxscope import NxscopeHandler

from nxscli.cli.environment import Environment, pass_environment

###############################################################################
# Command: cmd_dummy
###############################################################################


@click.group(name="dummy", chain=True)
@click.option("--writepadding", default=0)
@click.option(
    "--streamsleep",
    type=float,
    default=0.001,
    help="dummy dev parameter. Default: 0.001",
)
@click.option(
    "--samplesnum",
    type=int,
    default=100,
    help="dummy dev parameter. Default: 100",
)
@pass_environment
def cmd_dummy(
    ctx: Environment, writepadding: int, streamsleep: float, samplesnum: int
) -> bool:
    """[interface] Connect with a simulated NxScope devicve.

    \b
    Channels data:
      0: noise_uniform_scalar - vdim = 1, random()
      1: ramp_saw_up - vdim = 1, saw wave
      2: ramp_triangle - vdim = 1, triangle wave
      3: noise_uniform_vec2 - vdim = 2, random()
      4: noise_uniform_vec3 - vdim = 3, random()
      5: static_vec3 - vdim = 3, static vector = [1.0, 0.0, -1.0]
      6: text_hello_sparse - vdim = 1, sparse 'hello' string
      7: static_vec3_meta_counter - vdim = 3, static vec + 1B meta counter
      8: meta_hello_only - vdim = 0, mlen = 16, meta = 'hello string'
      9: sine_three_phase - vdim = 3, 3-phase sine wave
      10: reserved (undefined)
      11: fft_multitone - vdim = 1, deterministic multi-tone
      12: fft_chirp - vdim = 1, deterministic chirp-like signal
      13: hist_gaussian - vdim = 1, deterministic Gaussian-like
      14: hist_bimodal - vdim = 1, deterministic bi-modal
      15: xy_lissajous - vdim = 2, correlated XY signal
      16: polar_theta_radius - vdim = 2, (theta, radius) signal
      17: step_low_to_high - vdim = 1, one low-to-high step
      18: step_high_to_low - vdim = 1, one high-to-low step
      19: square_wave_20p - vdim = 1, periodic square wave (20% duty)
      20: impulse_sparse - vdim = 1, one-sample impulse every 250 samples
      21: square_wave_50p - vdim = 1, periodic square wave (50% duty)
      22: sine_slow - vdim = 1, slow sine wave
      23: impulse_clustered - vdim = 1, clustered impulses
      24: impulse_once_ref - vdim = 1, one-shot impulse reference
      25: vec3_mixed_steps - vdim = 3, mixed vector step source
    """  # noqa: D301
    intf = DummyDev(
        rxpadding=writepadding,
        stream_sleep=streamsleep,
        stream_snum=samplesnum,
    )

    # initialize nxslib communication handler
    assert ctx.parser
    ctx.nxscope = NxscopeHandler(
        intf,
        ctx.parser,
        enable_bitrate_tracking=True,
        stream_decode_mode="numpy",
    )

    ctx.interface = True

    return True
