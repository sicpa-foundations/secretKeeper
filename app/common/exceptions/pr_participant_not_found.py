class PRParticipantNotFound(Exception):
    """Raised when trying to update PR review status for a user
    who is not a participant of the PR."""

    def __init__(self, message=None):
        if message is None:
            message = "User is not a participant of PR"
        super().__init__(message)
