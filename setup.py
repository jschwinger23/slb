from setuptools import setup
from setuptools import find_packages

VERSION = '0.0.1'

setup(
    name='slb',
    url='https://github.com/jschwinger23/slb',
    description='Expelliarmus',
    packages=find_packages(),
    install_requires=[
        'click>=7.0,<8.0',
        'requests>=2.21.0,<3.0.0',
        'python-nginx>=1.5.3,<2.0.0',
    ],
    python_requires='>=3.7.1',
    entry_points={
        'console_scripts': [
            'slb=slb.cli:main',
        ]
    }
)
