# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from setup.page.setup_wizard.test_setup_data import args
from setup.page.setup_wizard.setup_wizard import setup_account

if __name__=="__main__":
	webnotes.connect()
	webnotes.local.form_dict = webnotes._dict(args)
	setup_account()
	