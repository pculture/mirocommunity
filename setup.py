from setuptools import setup, find_packages

version = 'master'

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
      localtv_update_thumbnails = localtv.feedimport:update_thumbnails
      """)


