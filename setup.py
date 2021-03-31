from setuptools import setup, find_packages

from os import path
from io import open

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='neoload-compose',
    include_package_data=True,
    packages=find_packages(exclude=("tests",)),
    entry_points={
        'console_scripts': [
            'neoload-compose=neoload_compose.__main__:cli',
            'neoloadc=neoload_compose.__main__:cli',
            'nlc=neoload_compose.__main__:cli'
        ]
    },
    setup_requires=['setuptools_scm'],
    use_scm_version={
        'write_to': 'neoload_compose/version.py',
        'write_to_template': '__version__ = "{version}"',
        'tag_regex': r'^(?P<prefix>v)?(?P<version>[^\+]+)(?P<suffix>.*)?$'
    },
    url='https://github.com/Neotys-Connect/neoload-compose',
    license='Apache 2.0',
    author='Paul Bruce',
    author_email='',
    description='A command-line native utility for creating NeoLoad performance tests',
    install_requires=[
        'click>=7',
        'pyconfig',
        'appdirs',
        'requests',
        'jsonschema',
        'PyYAML>=5',
        'pytest',
        'pytest-datafiles',
        'junit_xml',
        'termcolor',
        'coloredlogs',
        'gitignore_parser',
        'tqdm',
        'requests_toolbelt',
        'urllib3',
        'neoload',
        'colorama',
        'ruamel.yaml',
        'jsonpickle',
        'importlib-resources'
    ],
    long_description_content_type='text/markdown',
    long_description=long_description
)
