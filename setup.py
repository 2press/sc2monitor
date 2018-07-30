from setuptools import setup

setup(name='sc2monitor',
      version='0.1',
      description=('When executed regularly keeps track of large'
                   ' amount StarCraft 2 accounts on the 1vs1 ladder'),
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
