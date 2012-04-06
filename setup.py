from setuptools import setup, find_packages

__version__ = __import__('localtv').__version__

description = ("A Django app for creating a video website which aggregates from"
               " various sources - blip, Vimeo, youtube, etc. - rather than "
               "hosting video files.")

setup(name="mirocommunity",
      version='.'.join([str(v) for v in __version__]),
      url="http://mirocommunity.org",
      description=description,
      long_description=description,
      maintainer='Participatory Culture Foundation',
      maintainer_email='dev@mirocommunity.org',
      packages=find_packages(),
      include_package_data=True,
      classifiers=[
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'Intended Audience :: System Administrators',
          'License :: OSI Approved :: GNU Affero General Public License v3',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Topic :: Multimedia :: Sound/Audio',
          'Topic :: Multimedia :: Video',
      ],
      platforms=['OS Independent'],
      install_requires=['django>=1.4'])
