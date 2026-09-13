"""Deterministic source-grouped evaluation splits."""

from __future__ import annotations

import hashlib
from collections import defaultdict


def stable_grouped_split(
    records: list[dict],
    group_field: str = "parent_id",
    development_fraction: float = 0.4,
    seed: str = "aviation-rag-v1",
) -> dict[str, str]:
    if not 0 < development_fraction < 1:
        raise ValueError("development_fraction must be between 0 and 1")
    groups: dict[str, list[str]] = defaultdict(list)
    for record in records:
        groups[record[group_field]].append(record["qa_id"])
    if len(groups) < 2:
        raise ValueError("At least two source groups are required")

    def group_key(item: tuple[str, list[str]]) -> tuple[int, str]:
        group_id, qa_ids = item
        digest = hashlib.sha256(f"{seed}:{group_id}".encode("utf-8")).hexdigest()
        return -len(qa_ids), digest

    target_dev = round(len(records) * development_fraction)
    dev_count = 0
    test_count = 0
    assignments: dict[str, str] = {}
    ordered = sorted(groups.items(), key=group_key)

    for index, (group_id, qa_ids) in enumerate(ordered):
        remaining_groups = len(ordered) - index
        if remaining_groups == 1:
            split = "test" if test_count == 0 else "development"
        else:
            dev_error = abs(target_dev - (dev_count + len(qa_ids)))
            keep_error = abs(target_dev - dev_count)
            split = "development" if dev_error <= keep_error else "test"
        if split == "development":
            dev_count += len(qa_ids)
        else:
            test_count += len(qa_ids)
        for qa_id in qa_ids:
            assignments[qa_id] = split

    if not {"development", "test"} <= set(assignments.values()):
        raise ValueError("Both development and test splits must be non-empty")
    return assignments


def assert_group_disjoint(
    records: list[dict],
    assignments: dict[str, str],
    group_field: str = "parent_id",
) -> None:
    split_by_group: dict[str, set[str]] = defaultdict(set)
    for record in records:
        split_by_group[record[group_field]].add(assignments[record["qa_id"]])
    leaking = [group for group, splits in split_by_group.items() if len(splits) > 1]
    if leaking:
        raise ValueError(f"Source groups leak across splits: {sorted(leaking)}")
