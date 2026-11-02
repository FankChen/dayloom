class KnownFailure(Exception):
    status = "failed"
    public_message = (
        "The external service rejected the operation before accepting it. Review before retrying."
    )


class AuthorityRevoked(Exception):
    status = "cancelled"
    public_message = "The automation authority expired, changed or was revoked. Nothing further will be executed."


class OutcomeUnknown(Exception):
    status = "outcome_unknown"
    public_message = "The external result is uncertain. Check the provider before creating another action; automatic retry is disabled."
