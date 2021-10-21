from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import yaml

from typing import Optional, Any

from tasdmc import fileio
from .utils import datetime2str


class EventType(Enum):
    STARTED = 'started'
    SKIPPED = 'skipped'
    COMPLETED = 'completed'
    FAILED = 'failed'
    OUTPUT_SIZE_MEASURED = 'output_size_measured'

    def __str__(self) -> str:
        return self.value


@dataclass
class PipelineStepProgress:
    event_type: EventType
    step_name: str
    step_input_hash: str
    step_description: str
    timestamp: datetime
    pipeline_id: str
    value: Optional[Any] = None

    def save(self):
        d = asdict(self)
        d.pop('pipeline_id')
        d['timestamp'] = datetime2str(self.timestamp)
        if self.value is None:
            d.pop('value')
        with open(fileio.pipeline_log(self.pipeline_id), 'a') as f:
            yaml.dump([{key: str(d[key]) for key in sorted(d.keys())}], f)

    @classmethod
    def from_step(
        cls, step: 'FileInFileOutPipelineStep', event_type: EventType, value: Optional[Any] = None  # type: ignore
    ) -> PipelineStepProgress:
        return PipelineStepProgress(
            event_type,
            step_name=step.__class__.__name__,
            step_input_hash=step.input_.contents_hash,
            step_description=step.description,
            timestamp=datetime.utcnow(),
            pipeline_id=step.pipeline_id,
            value=value,
        )


def started(step: 'FileInFileOutPipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.STARTED).save()


def skipped(step: 'FileInFileOutPipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.SKIPPED).save()


def completed(step: 'FileInFileOutPipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.COMPLETED).save()


def failed(step: 'FileInFileOutPipelineStep', errmsg: str):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.FAILED, value=errmsg).save()


def output_size_measured(step: 'FileInFileOutPipelineStep', output_size_mb: int):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.OUTPUT_SIZE_MEASURED, value=output_size_mb).save()