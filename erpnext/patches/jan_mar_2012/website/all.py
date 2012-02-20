import patches.jan_mar_2012.website.login
import patches.jan_mar_2012.website.feed
import patches.jan_mar_2012.website.website
import patches.jan_mar_2012.website.cleanups
import patches.jan_mar_2012.website.domain_list
import patches.jan_mar_2012.website.file_data_rename
import patches.jan_mar_2012.website.analytics


def execute():
	patches.jan_mar_2012.website.login.execute()
	patches.jan_mar_2012.website.feed.execute()
	patches.jan_mar_2012.website.website.execute()
	patches.jan_mar_2012.website.cleanups.execute()
	patches.jan_mar_2012.website.domain_list.execute()
	patches.jan_mar_2012.website.file_data_rename.execute()
	patches.jan_mar_2012.website.analytics.execute()
