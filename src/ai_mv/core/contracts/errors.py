class PipelineError(RuntimeError):
    pass


class StageFailure(PipelineError):
    pass


class ComfyRequestError(PipelineError):
    pass


class CodexCliRequestError(PipelineError):
    pass


class WorkflowValidationError(PipelineError):
    pass


class MediaValidationError(PipelineError):
    pass
