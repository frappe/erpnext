def execute():
	"""drop and create __CacheItem table again"""
	import webnotes
	webnotes.conn.commit()
	webnotes.conn.sql("drop table __CacheItem")
	webnotes.conn.sql("""create table __CacheItem(
		`key` VARCHAR(180) NOT NULL PRIMARY KEY,
		`value` LONGTEXT,
		`expires_on` DATETIME
		) ENGINE=MyISAM DEFAULT CHARSET=utf8""")
	webnotes.conn.begin()