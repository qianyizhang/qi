"""Compatibility exports for the unchanged v1 dataset format and generator."""

from qi.training_data.legacy import (
    MAX_LABELS,
    MAX_SOURCES,
    Dataset,
    Label,
    SourceGame,
    generate,
    reserved_inputs,
    teacher_identity,
)

__all__ = [
    "MAX_LABELS",
    "MAX_SOURCES",
    "Dataset",
    "Label",
    "SourceGame",
    "generate",
    "reserved_inputs",
    "teacher_identity",
]
