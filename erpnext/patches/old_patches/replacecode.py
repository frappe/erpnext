# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

def replace_code(old, new):
	txt = os.popen("""grep "%s" ./*/*/*/*.js""" % old).read().split()
	txt = [t.split(':')[0] for t in txt]
	txt = list(set(filter(lambda t: t.startswith('./'), txt)))
	for t in txt:
		if new:
			code = open(t,'r').read().replace(old, new)
			open(t, 'w').write(code)
			print "Replaced for %s" % t
		else:
			print 'Found in %s' % t
	
if __name__=='__main__':
	old = """cur_frm.cscript.get_tips(doc, cdt, cdn);"""
	new = " "
	replace_code(old, new)
			
