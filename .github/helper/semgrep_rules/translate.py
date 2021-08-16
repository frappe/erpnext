# Examples taken from https://frappeframework.com/docs/user/en/translations
# This file is used for testing the tests.

from frappe import _

full_name = "Jon Doe"
# ok: frappe-translation-python-formatting
_('Welcome {0}, get started with ERPNext in just a few clicks.').format(full_name)

# ruleid: frappe-translation-python-formatting
_('Welcome %s, get started with ERPNext in just a few clicks.' % full_name)
# ruleid: frappe-translation-python-formatting
_('Welcome %(name)s, get started with ERPNext in just a few clicks.' % {'name': full_name})

# ruleid: frappe-translation-python-formatting
_('Welcome {0}, get started with ERPNext in just a few clicks.'.format(full_name))


subscribers = ["Jon", "Doe"]
# ok: frappe-translation-python-formatting
_('You have {0} subscribers in your mailing list.').format(len(subscribers))

# ruleid: frappe-translation-python-splitting
_('You have') + len(subscribers) + _('subscribers in your mailing list.')

# ruleid: frappe-translation-python-splitting
_('You have {0} subscribers \
    in your mailing list').format(len(subscribers))

# ok: frappe-translation-python-splitting
_('You have {0} subscribers') \
    + 'in your mailing list'

# ruleid: frappe-translation-trailing-spaces
msg = _(" You have {0} pending invoice ")
# ruleid: frappe-translation-trailing-spaces
msg = _("You have {0} pending invoice ")
# ruleid: frappe-translation-trailing-spaces
msg = _(" You have {0} pending invoice")

# ok: frappe-translation-trailing-spaces
msg = ' ' + _("You have {0} pending invoices") + ' '

# ruleid: frappe-translation-python-formatting
_(f"can not format like this - {subscribers}")
# ruleid: frappe-translation-python-splitting
_(f"what" + f"this is also not cool")


# ruleid: frappe-translation-empty-string
_("")
# ruleid: frappe-translation-empty-string
_('')


class Test:
	# ok: frappe-translation-python-splitting
	def __init__(
			args
			):
		pass
