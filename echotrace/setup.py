from setuptools import setup, find_packages
setup(
    name="echotrace",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["sqlalchemy>=2.0"],
)
