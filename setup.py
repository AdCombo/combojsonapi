import pathlib
import pip

from setuptools import setup, find_packages

__version__ = "1.0.0"

from packaging import version

try:
    from pip.req import parse_requirements
except ImportError:  # pip >= 10.0.0
    from pip._internal.req import parse_requirements

WORK_DIR = pathlib.Path(__file__).parent

NEW_PIP_REQ_VERSION = '20.1'
"""Minimal version with a new broken attribute for parse requirements file."""


def get_requirements(filename=None):
    """
    https://stackoverflow.com/questions/14399534/reference-requirements-txt-for-the-install-requires-kwarg-in
    -setuptools-setup-py

    Read requirements from 'requirements txt'
    :return: requirements
    :rtype: list
    """
    if filename is None:
        filename = "requirements.txt"

    file = WORK_DIR / filename
    if version.parse(pip.__version__) >= version.parse(NEW_PIP_REQ_VERSION):
        attr = 'requirement'
    else:
        attr = 'req'
    install_reqs = parse_requirements(str(file), session="hack")
    return [str(getattr(ir, attr)) for ir in install_reqs]


setup(
    name="ComboJSONAPI",
    version=__version__,
    description="REST JSONAPI extension to create web api (currently only flask is supported)",
    # TODO: separate desription for pypi
    url="https://github.com/AdCombo/combojsonapi",
    author="AdCombo API Team",
    author_email="",  # TODO
    license="MIT",  # TODO: discuss
    classifiers=[
        "Framework :: Flask",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: MIT License",
    ],
    keywords="web api rest rpc swagger jsonapi flask sqlalchemy marshmallow plugin",
    packages=find_packages(exclude=["tests"]),
    zip_safe=False,
    platforms="any",
    # this would'n work now
    install_requires=get_requirements(),
    # todo maybe just write all requirements here? stop usin requirements.txt?
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    extras_require={"tests": "pytest", "docs": "sphinx"},
)
