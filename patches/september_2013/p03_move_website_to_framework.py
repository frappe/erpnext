# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes
from webnotes.utils import get_base_path
import os, shutil

def execute():
	# remove pyc files
	utils_pyc = os.path.join(get_base_path(), "app", "selling", "utils.pyc")
	if os.path.exists(utils_pyc):
		os.remove(utils_pyc)
	
	old_path = os.path.join(get_base_path(), "app", "website")
	if os.path.exists(old_path):
		shutil.rmtree(old_path)