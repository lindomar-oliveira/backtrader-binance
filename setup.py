import os
from setuptools import setup

with open(os.path.join('requirements.txt')) as reqs:
    REQUIREMENTS = reqs.readlines()

setup(
    name='backtrader-binance',
    version='1.0',
    description='Binance API integration with backtrader',
    keywords='backtrader,binance,bitcoin,bot,crypto,trading',
    url='https://github.com/lindomar-oliveira/backtrader-binance',
    author='Lindomar Oliveira',
    author_email='lindomar.souza1999@gmail.com',
    license='MIT',
    packages=['backtrader_binance'],
    install_requires=REQUIREMENTS
)
