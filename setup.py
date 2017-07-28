#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup, find_packages


setup(
    name='bounced_email_service',
    version='0.1.0',
    description='This service detects bounced emails',
    author='matthias wiesner',
    packages=find_packages(exclude='tests'),
    install_requires=[
        'PyYaml',
        'Click',
        'pika',
        'flufl.bounce',
        'validate_email',
        'tldextract',
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'bouncedemails=bounced_email_service.service:main'
        ]
    }
)