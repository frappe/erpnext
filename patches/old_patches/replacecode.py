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
			
