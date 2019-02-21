"""Set up the sc2monitor via setuptools."""
from os import path

from setuptools import setup

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(name='sc2monitor',
      version='0.2.30',
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
          'pytest >= 4.3.0',
          'pytest-cov >= 2.6.1',
          'codecov >= 2.0.15'
      ],
      packages=['sc2monitor'],
      install_requires=[
          'PyMySQL >= 0.9.3',
          'aiohttp >= 3.5.4',
          'sqlalchemy >= 1.2.18'
      ],
      zip_safe=False,
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Environment :: Console',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8'])
