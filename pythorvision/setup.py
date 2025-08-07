# setup.py
from setuptools import setup, find_packages

setup(
    name="pythorvision",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
    ],
    author="Kontex",
    author_email="hhuang@kontex.com",
    description="Python API for ThorVision",
    keywords="vision, camera, api",
    python_requires=">=3.6",
)