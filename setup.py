import os
from setuptools import setup

with open(os.path.join('README.md')) as desc:
    LONG_DESCRIPTION = desc.read()

with open(os.path.join('requirements.txt')) as reqs:
    REQUIREMENTS = reqs.readlines()

setup(
    name='backtrader-binance',
    version='1.0.0',
    description='Binance API integration with backtrader',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://github.com/lindomar-oliveira/backtrader-binance',
    author='Lindomar Oliveira',
    author_email='lindomar.souza1999@gmail.com',
    license='MIT',
    packages=['backtrader_binance'],
    python_requires='>=3.7',
    keywords='backtrader,binance,bitcoin,bot,crypto,trading',
    install_requires=REQUIREMENTS
)
