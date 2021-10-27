from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from typing import Optional, Any, List

from tasdmc import fileio

# from tasdmc.steps.base import FileInFileOutPipelineStep
from .utils import datetime2str, str2datetime


class EventType(Enum):
    STARTED = 'started'
    SKIPPED = 'skipped'
    COMPLETED = 'completed'
    FAILED = 'failed'
    OUTPUT_SIZE_MEASURED = 'output_size_measured'  # DEPRECATED, kept for older runs

    def __str__(self) -> str:
        return self.value


@dataclass
class PipelineStepProgress:
    event_type: EventType
    step_name: str
    step_input_hash: str
    timestamp: datetime
    pipeline_id: str
    value: Optional[Any] = None

    def save(self):
        export_fields = [
            datetime2str(self.timestamp),
            self.pipeline_id,
            self.step_name,
            self.step_input_hash,
            str(self.event_type),
        ]
        if self.value is not None:
            export_fields.append(str(self.value))
        with open(fileio.pipelines_log(), 'a') as f:
            f.write(' '.join(export_fields) + '\n')

    @classmethod
    def load(cls) -> List[PipelineStepProgress]:
        step_progresses = []
        for line in fileio.pipelines_log().read_text().splitlines():
            datetime_str, pipeline_id, step_name, step_input_hash, event_type_str, *rest = line.split(' ')
            step_progresses.append(
                PipelineStepProgress(
                    timestamp=str2datetime(datetime_str),
                    pipeline_id=pipeline_id,
                    step_name=step_name,
                    step_input_hash=step_input_hash,
                    event_type=EventType(event_type_str),
                    value=rest[0] if rest else None,
                )
            )
        return step_progresses

    @classmethod
    def from_step(
        cls, step: 'FileInFileOutPipelineStep', event_type: EventType, value: Optional[Any] = None  # type: ignore
    ) -> PipelineStepProgress:
        return PipelineStepProgress(
            event_type,
            step_name=step.__class__.__name__,
            step_input_hash=step.input_.contents_hash,
            timestamp=datetime.utcnow(),
            pipeline_id=step.pipeline_id,
            value=value,
        )


def started(step: 'FileInFileOutPipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.STARTED).save()


def skipped(step: 'FileInFileOutPipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.SKIPPED).save()


def completed(step: 'FileInFileOutPipelineStep', output_size_mb: int):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.COMPLETED, value=output_size_mb).save()


def failed(step: 'FileInFileOutPipelineStep', errmsg: str):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.FAILED, value=errmsg).save()
