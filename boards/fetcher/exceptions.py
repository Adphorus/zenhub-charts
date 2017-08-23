class PipelineNotFoundError(Exception):
    def __init__(self, board, name):
        message = f'Pipeline ({name}) not found in {board} boards'
        super(PipelineNotFoundError, self).__init__(message)
