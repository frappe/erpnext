# Copyright (c) 2013, Web Notes Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import webnotes

from webnotes.model import db_exists
from webnotes.model.bean import copy_doclist

	


class DocType:
  def __init__(self,d,dl):
    self.doc, self.doclist = d, dl
	
def on_doctype_update():
	if not webnotes.conn.sql("""show index from `tabFeed` 
		where Key_name="feed_doctype_docname_index" """):
		webnotes.conn.commit()
		webnotes.conn.sql("""alter table `tabFeed` 
			add index feed_doctype_docname_index(doc_type, doc_name)""")