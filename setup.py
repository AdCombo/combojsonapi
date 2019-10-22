from setuptools import setup, find_packages


__version__ = '0.1.0'


setup(
    name="ComboJSONAPI",
    version=__version__,
    description='Flask-REST-JSONAPI extension to create web api',
    url='',
    author='AdCombo API Team',
    author_email='',
    license='MIT',
    classifiers=[
        'Framework :: Flask',
        'Programming Language :: Python :: 3.6',
        'License :: OSI Approved :: MIT License',
    ],
    keywords='web api rest rpc swagger jsonapi flask sqlalchemy marshmallow',
    packages=find_packages(exclude=['tests']),
    zip_safe=False,
    platforms='any',
    install_requires=['Flask>=1.0.2',
                      'flask-rest-jsonapi',
                      'marshmallow_jsonapi',
                      'apispec>=2.0.2',
                      'sqlalchemy'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest'],
    extras_require={'tests': 'pytest', 'docs': 'sphinx'}
)
