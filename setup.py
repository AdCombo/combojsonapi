import os

from setuptools import setup, find_packages

__version__ = "1.1.0"


requirements_filepath = os.path.join(os.path.dirname(__name__), "requirements.txt")
with open(requirements_filepath) as fp:
    install_requires = fp.read()


setup(
    name="ComboJSONAPI",
    version=__version__,
    description="4 plugins for Flask-COMBO-JSONAPI package.",
    url="https://github.com/AdCombo/combojsonapi",
    author="AdCombo Team",
    author_email="roman@adcombo.com",
    license="MIT",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Framework :: Flask",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Topic :: Internet",
    ],
    keywords="web api rest rpc swagger jsonapi flask sqlalchemy marshmallow plugin",
    packages=find_packages(exclude=["tests"]),
    package_data={"": ["apispec/templates/*.html"]},
    include_package_data=True,
    zip_safe=False,
    platforms="any",
    install_requires=install_requires,
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    extras_require={"tests": "pytest", "docs": "sphinx"},
)
