import os
from distutils.core import setup


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name='django-workflow',
    version='0.0.1',
    description="A lightweight workflow engine application for Django based web-applications.",
    long_description=read('README.txt'),
    author='pysaoke',
    author_email='',
    license='MIT',
    url='http://github.com/baixuexue123/django-workflow',
    packages=[
        'workflow',
    ],
    include_package_data=True,
    install_requires=[
    ],

    zip_safe=False,
    keywords='django-workflow',

    classifiers=[
        'Development Status :: 1 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)
