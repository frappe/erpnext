import patches.jan_mar_2012.website.login
import patches.jan_mar_2012.website.feed
import patches.jan_mar_2012.website.website
import patches.jan_mar_2012.website.cleanups

def execute():
	patches.jan_mar_2012.website.login.execute()
	patches.jan_mar_2012.website.feed.execute()
	patches.jan_mar_2012.website.website.execute()
	patches.jan_mar_2012.website.cleanups.execute()