from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from typing import Optional, Any, List

from tasdmc import fileio

# from tasdmc.steps.base import PipelineStep
from .utils import datetime2str, str2datetime


class EventType(Enum):
    STARTED = 'started'
    SKIPPED = 'skipped'
    COMPLETED = 'completed'
    FAILED = 'failed'

    def __str__(self) -> str:
        return self.value


@dataclass
class PipelineStepProgress:
    event_type: EventType
    step_name: str
    step_id: str
    timestamp: datetime
    pipeline_id: str
    value: Optional[Any] = None

    def save(self):
        export_fields = [
            datetime2str(self.timestamp),
            self.pipeline_id,
            self.step_name,
            self.step_id,
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
            try:
                datetime_str, pipeline_id, step_name, step_id, event_type_str, *rest = line.split(' ')
            except ValueError:
                continue
            rest = ' '.join(rest)
            event_type = EventType(event_type_str)
            if event_type is EventType.COMPLETED and rest:
                value = float(rest)
            elif event_type is EventType.FAILED and rest:
                value = rest
            else:
                value = None
            step_progresses.append(
                PipelineStepProgress(
                    timestamp=str2datetime(datetime_str),
                    pipeline_id=pipeline_id,
                    step_name=step_name,
                    step_id=step_id,
                    event_type=event_type,
                    value=value,
                )
            )
        return step_progresses

    @classmethod
    def from_step(
        cls, step: 'PipelineStep', event_type: EventType, value: Optional[Any] = None  # type: ignore
    ) -> PipelineStepProgress:
        try:
            step_id = step.get_id()
        except Exception as e:
            e_no_spaces = str(e).replace(" ", "-")
            step_id = f"CANNOT-CALCULATE-STEP-ID-{e_no_spaces}"
        return PipelineStepProgress(
            event_type,
            step_name=step.name,
            step_id=step_id,
            timestamp=datetime.utcnow(),
            pipeline_id=step.pipeline_id,
            value=value,
        )


def started(step: 'PipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.STARTED).save()


def skipped(step: 'PipelineStep'):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.SKIPPED).save()


def completed(step: 'PipelineStep', output_size_mb: int):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.COMPLETED, value=output_size_mb).save()


def failed(step: 'PipelineStep', errmsg: str):  # type: ignore
    PipelineStepProgress.from_step(step, EventType.FAILED, value=errmsg.replace('\n', ' ')).save()
