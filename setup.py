"""Set up the sc2monitor via setuptools."""
from os import path

from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='sc2monitor',
      version='0.2.38',
      description=('When executed regularly keeps track of medium'
                   ' amount of StarCraft 2 accounts on the 1vs1 ladder'),
      long_description=long_description,
      long_description_content_type='text/markdown',
      url='https://github.com/2press/sc2monitor',
      author='pressure',
      author_email='pres.sure@ymail.com',
      license='MIT',
      python_requires='>=3.7.1',
      tests_require=[
          'pytest >= 6.0.1',
          'pytest-cov >= 2.10.1',
          'codecov >= 2.1.9'
      ],
      packages=['sc2monitor'],
      install_requires=[
          'PyMySQL >= 0.10.0',
          'aiohttp >= 3.6.2',
          'sqlalchemy==1.3.19'
      ],
      zip_safe=False,
      classifiers=[
          'Development Status :: 4 - Beta',
          'Environment :: Console',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8'])
