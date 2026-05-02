import logging

logger = logging.getLogger(__name__)


def send_decision_email(application):
    """
    Notify the doctor of the review decision.
    TODO: replace the log statements below with real email sending
          e.g. Django's send_mail() or an email service like SendGrid.
    """
    if application.status == 'approved':
        _send_approval_email(application)
    elif application.status == 'rejected':
        _send_rejection_email(application)


def _send_approval_email(application):
    # TODO: replace with real send_mail() call
    logger.info(
        "[EMAIL STUB] Approval email to %s <%s> | Application ID: %s",
        application.full_name,
        application.email,
        application.pk,
    )
    print(
        f"\n[EMAIL STUB] TO: {application.email}\n"
        f"SUBJECT: Your application has been approved\n"
        f"BODY: Dear {application.full_name}, congratulations! "
        f"Your application to join Mental Space has been approved.\n"
    )


def _send_rejection_email(application):
    # TODO: replace with real send_mail() call
    logger.info(
        "[EMAIL STUB] Rejection email to %s <%s> | Application ID: %s | Reason: %s",
        application.full_name,
        application.email,
        application.pk,
        application.rejection_reason,
    )
    print(
        f"\n[EMAIL STUB] TO: {application.email}\n"
        f"SUBJECT: Update on your application\n"
        f"BODY: Dear {application.full_name}, unfortunately your application "
        f"has not been approved.\nReason: {application.rejection_reason}\n"
    )
