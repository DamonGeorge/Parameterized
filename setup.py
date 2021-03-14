from setuptools import setup

# get current version
exec(open("parameterized/_version.py").read())

setup(
    name="Parameterized",
    url="https://github.com/DamonGeorge/Parameterized",
    author="Damon George",
    author_email="damon@kindgeorge.com",
    packages=["parameterized"],
    install_requires=["numpy"],
    version=__version__,  # pylint: disable=E0602
    license="MIT",
    description="A simple Python library for creating Parameterized objects that can be saved and loaded to or from dictionaries (and json).",
    long_description=open("README.md").read(),
)
