from setuptools import setup, find_packages

setup(
    name='imgurdl',
    packages=find_packages(),
    entry_points = {
        'console_scripts': [
            'imgur-dl = imgurdl.__main__:main'
        ]
    }
)
