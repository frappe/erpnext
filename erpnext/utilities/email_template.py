import frappe


def get_email_subject_and_message(
	template_name: str | None, context: dict, default_subject: str, default_message: str
) -> tuple[str, str]:
	"""Render the Email Template with `context`, or return the defaults when no template is set."""
	if not template_name:
		return default_subject, default_message

	template = frappe.get_cached_doc("Email Template", template_name)
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	subject = frappe.render_template(template.subject, context, restrict_globals=True)
	# nosemgrep: frappe-semgrep-rules.rules.security.frappe-ssti
	message = frappe.render_template(template.response_, context, restrict_globals=True)
	return subject, message
