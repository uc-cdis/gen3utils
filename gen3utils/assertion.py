from cdislogging import get_logger

logger = get_logger("gen3utils", log_level="info")


def assert_and_log(assertion_success, error_message):
    """
    If an assertion fails, logs the provided error message and updates
    the global variable "failed_validation" for future use.

    Args:
        assertion_success (bool): result of an assertion.
        error_message (str): message to display if the assertion failed.

    Return:
        assertion_success(bool): result of the assertion.
    """
    if not assertion_success:
        logger.error(error_message)
    return bool(assertion_success)
