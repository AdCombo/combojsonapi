from setuptools import setup, find_packages

__version__ = "1.0.2"

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
    install_requires=[
        'sqlalchemy',
        'marshmallow==3.2.1',
        'marshmallow_jsonapi==0.22.0',
        'Flask>=1.0.1',
        'apispec>=2.0.2',
        'flask-combo-jsonapi @ git+https://github.com/AdCombo/flask-combo-jsonapi.git@1.0.0',
    ],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    extras_require={"tests": "pytest", "docs": "sphinx"},
)
