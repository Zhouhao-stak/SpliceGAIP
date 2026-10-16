"""Splicing subpackage: standardized alternative-splicing data layer.

The event contract mirrors the production ``AS_event_master`` schema of
SplicingNexus v2 so that both platforms can exchange event tables without
conversion.
"""

from splicegaip.splicing.schema import (
    AS_EVENT_FIELDS,
    AS_EVENT_TYPES,
    SampleMetadata,
    StandardEvent,
    load_events_tsv,
    load_sample_metadata,
)

__all__ = [
    "AS_EVENT_FIELDS",
    "AS_EVENT_TYPES",
    "SampleMetadata",
    "StandardEvent",
    "load_events_tsv",
    "load_sample_metadata",
]
