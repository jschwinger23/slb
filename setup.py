from setuptools import setup
from setuptools import find_packages


VERSION = '0.0.1'

setup(
    name='slb',
    url='https://github.com/jschwinger23/slb',
    description='Expelliarmus',
    author='zc',
    author_email='greychwinger@gmail.com',
    packages=find_packages(),
    install_requires=[
        'click>=7.0,<8.0',
    ],
    python_requires='>=3.6.1',
)
