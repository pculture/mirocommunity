from setuptools import setup, find_packages

version = '1.2.0'

setup(name="Miro Community",
      version=version,
      packages=find_packages(),
      author='Participatory Culture Foundation',
      license='AGPLv3',
      install_requires=['django==1.2.5'])


