class PipelineNotFoundError(Exception):
    def __init__(self, repo, name):
        message = f'Pipeline ({name}) not found in {repo} boards'
        super(PipelineNotFoundError, self).__init__(message)
