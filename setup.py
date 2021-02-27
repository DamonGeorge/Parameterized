from setuptools import setup

setup(
    # Needed to silence warnings (and to be a worthwhile package)
    name='Parmeterized',
    url='https://github.com/DamonGeorge/Parameterized',
    author='Damon George',
    author_email='georgdam@oregonstate.du',
    # Needed to actually package something
    packages=['parameterized'],
    # Needed for dependencies
    install_requires=['numpy'],
    # *strongly* suggested for sharing
    version='0.1',
    # The license can be anything you like
    license='MIT',
    description='A simple Python library for creating Parameterized objects that can be saved and loaded to or from dictionaries (and json).',
    # We will also need a readme eventually (there will be a warning)
    long_description=open('README.md').read(),
)
