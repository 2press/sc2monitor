from setuptools import setup

# read the contents of README file
from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='sc2monitor',
      version='0.1',
      description=('When executed regularly keeps track of large'
                   ' amount StarCraft 2 accounts on the 1vs1 ladder'),
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/2press/sc2monitor',
      author='pressure',
      author_email='pres.sure@ymail.com',
      license='MIT',
      packages=['sc2monitor'],
      install_requires=[
          'PyMySQL',
          'requests'
      ],
      zip_safe=False)
