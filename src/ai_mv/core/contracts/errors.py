class PipelineError(RuntimeError):
    pass


class StageFailure(PipelineError):
    pass


class ComfyRequestError(PipelineError):
    pass


class OllamaRequestError(PipelineError):
    pass


class WorkflowValidationError(PipelineError):
    pass


class MediaValidationError(PipelineError):
    pass
