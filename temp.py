license = """ERPNext - web based ERP (http://erpnext.com)
Copyright (C) 2012 Web Notes Technologies Pvt Ltd

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>."""

license2 = """Copyright (c) 2012 Web Notes Technologies Pvt Ltd (http://erpnext.com)

MIT License (MIT)

Permission is hereby granted, free of charge, to any person obtaining a 
copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation 
the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in 
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF 
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE 
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


if __name__=='__main__':
	import os
	#clicense = '\n'.join([('# ' + l) for l in license2.split('\n')])
	cnt = 0	
	for wt in os.walk('.'):
		for fname in wt[2]:
			if fname.endswith('.js'):
				cnt += 1
				#path = os.path.join(wt[0], fname)
				#with open(path, 'r') as codefile:
				#	codetxt = codefile.read()
				
				#if codetxt.strip():
				#	with open(path, 'w') as codefile:
				#		codefile.write(clicense + '\n\n' + codetxt)
				
				#	print 'updated in ' + path	
	print cnt
