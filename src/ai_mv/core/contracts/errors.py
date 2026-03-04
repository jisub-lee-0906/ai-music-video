class PipelineError(RuntimeError):
    pass


class StageFailure(PipelineError):
    pass

