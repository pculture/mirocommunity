from setuptools import setup, find_packages

version = '0.9-pre'

setup(name="Miro Community",
      version=version,
      author='Participatory Culture Foundation',
      license='AGPLv3',
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      localtv_update_feeds = localtv.feedimport:update_feeds
      localtv_update_saved_searches = localtv.feedimport:update_saved_searches
      localtv_update_publish_date = localtv.feedimport:update_publish_date
      """)


