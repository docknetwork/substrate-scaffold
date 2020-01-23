from setuptools import setup

setup(
    name='dockinfra',
    version='0.1',
    py_modules=['dockinfra'],
    install_requires=[
        'awscli',
        'boto3',
        'paramiko',
        'Click',
    ],
    entry_points='''
        [console_scripts]
        dockinfra=dockinfra:main
    ''',
)
