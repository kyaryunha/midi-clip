from setuptools import setup, find_packages
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


setup(
    name="midi-clip",
    version="0.7",
    packages=find_packages(),
    description="A python package for midi clip.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="kyaryunha",
    author_email="kyaryunha@gmail.com",
    url="https://github.com/kyaryunha/midi-clip",
    install_requires=[
        "mido",
    ],
)
