"""
Tool for send emails and return the status of the requisition (mock tool).
"""


def send_email(
    title: str,
    to: str | list[str],
    content: str
) -> dict:
    """
    Send an email to one or many users.

    Args:
        title (str): the content that will be in the title of the email
        to (str | list[str]): the person or the list of recipients of the email
        content (str): the content that will be in the body of the email

    Returns:
        dict: The query results and status
    """
    return {
        "status": "success",
        "message": f"Successfully sent email to '{to}'",
    }
