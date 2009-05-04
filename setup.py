from setuptools import setup, find_packages

version = '0.0.1'

setup(name="Miro Local TV",
      version=version,
      author='Participatory Culture Foundation',
      license='AGPLv3',
      entry_points="""
      # -*- Entry points: -*-
      [console_scripts]
      localtv_update_feeds = localtv.feedimport:update_feeds
      localtv_update_saved_searches = localtv.feedimport:update_saved_searches
      """)
      


