import webnotes
from webnotes.utils import cint

def execute():	
	import patches.march_2013.p08_create_aii_accounts
	patches.march_2013.p08_create_aii_accounts.execute()