========
Triggers
========

Overview
========

Nxscli supports software triggers configured globally with ``trig`` or
per-plugin with ``--trig``.

Current trigger types:

* ``on`` - always on
* ``off`` - always off
* ``er`` - edge rising
* ``ef`` - edge falling
* ``we`` - window enter
* ``wx`` - window exit

Current capture modes:

* ``mode=start_after`` - default behavior, emit data only after trigger
* ``mode=stop_after`` - stream data until trigger, then stop after ``post``
  samples

Syntax
======

Format:

.. code-block:: text

   [channel]:[trigger][#source][@vector],[legacy_hoffset],[level_or_low][,high][,name=value...]

Supported named options:

* ``mode=start_after|stop_after``
* ``pre=<samples>`` - explicit pre-trigger samples for start-after capture
* ``post=<samples>`` - post-trigger samples for stop-after capture
* ``holdoff=<samples>`` - reserved for upcoming repeated/scope modes
* ``rearm=true|false`` - reserved for upcoming repeated/scope modes

Notes:

* The positional ``hoffset`` field is preserved for backward compatibility and
  currently acts as legacy pre-trigger history.
* Advanced trigger capture modes currently target NumPy block streams.
* Trigger source can be cross-channel via ``#chan`` and vector index via
  ``@idx``.
* Window triggers use positional parameters ``hoffset,low,high``.

Trigger Semantics
=================

All edge and window triggers are evaluated on consecutive sample pairs.
That means the trigger boundary is defined between sample ``n`` and
sample ``n+1``, not "on" one single sample value.

Edge triggers:

* ``er`` fires when sample ``n`` is at or below ``level`` and sample
  ``n+1`` is above ``level``.
* ``ef`` fires when sample ``n`` is at or above ``level`` and sample
  ``n+1`` is below ``level``.

Window triggers:

* ``we`` fires when sample ``n`` is outside ``[low, high]`` and sample
  ``n+1`` is inside ``[low, high]``.
* ``wx`` fires when sample ``n`` is inside ``[low, high]`` and sample
  ``n+1`` is outside ``[low, high]``.

Trigger Boundary
================

For ``er``, ``ef``, ``we``, and ``wx``, the trigger point belongs to the
transition between sample ``n`` and sample ``n+1``.

That means these triggers are boundary-based, not whole-sample events.
Any downstream consumer should treat the trigger position as the crossing
between the two samples that satisfied the trigger condition.

Downstream Delivery
===================

Trigger events are delivered together with normal stream payload handling.
Plugins first read triggered data from their queue, then read the matching
trigger event metadata for that payload batch.

The trigger event metadata currently includes:

* trigger position within the emitted payload
* channel id associated with the emitted event
* capture mode

Examples
========

Always on:

.. code-block:: bash

   python -m nxscli dummy trig "g:on" chan 17 pprinter 8

Start after trigger with pre-trigger history:

.. code-block:: bash

   python -m nxscli dummy trig "g:er#17,0,0.5,pre=16" chan 17 pnpsave 64 /tmp/nxs_trigger_pre

Stop after trigger with post-trigger tail:

.. code-block:: bash

   python -m nxscli dummy trig "g:er#17,0,0.5,mode=stop_after,post=32" chan 17 pnpsave 256 /tmp/nxs_trigger_post

Vector trigger on deterministic mixed vector channel:

.. code-block:: bash

   python -m nxscli dummy trig "g:er#25@1,0,0.5,pre=8" chan 25 pnpsave 64 /tmp/nxs_trigger_vec

Window enter trigger on deterministic sine source:

.. code-block:: bash

   python -m nxscli dummy trig "g:we#22,0,-0.25,0.25,pre=16" chan 22 pnpsave 64 /tmp/nxs_trigger_window_enter

Window exit trigger on deterministic sine source:

.. code-block:: bash

   python -m nxscli dummy trig "g:wx#22,0,-0.25,0.25,pre=16" chan 22 pnpsave 64 /tmp/nxs_trigger_window_exit
