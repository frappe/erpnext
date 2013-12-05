# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist

	


class DocType:
  def __init__(self,doc,doclist=[]):
    self.doc, self.doclist = doc,doclist