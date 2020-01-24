"""
This is a file to describe the Python module distribution and
helps with installation.

More info on various arguments here:
https://setuptools.readthedocs.io/en/latest/setuptools.html
"""
from setuptools import setup, find_packages
from subprocess import check_output


def get_version():
    # https://github.com/uc-cdis/dictionaryutils/pull/37#discussion_r257898408
    try:
        tag = check_output(
            ["git", "describe", "--tags", "--abbrev=0", "--match=[0-9]*"]
        )
        return tag.decode("utf-8").strip("\n")
    except Exception:
        raise RuntimeError(
            "The version number cannot be extracted from git tag in this source "
            "distribution; please either download the source from PyPI, or check out "
            "from GitHub and make sure that the git CLI is available."
        )


def get_readme():
    with open("README.md", "r") as f:
        return f.read()


setup(
    name="gen3utils",
    version=get_version(),
    description="Gen3 Library Template",
    long_description=get_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/uc-cdis/gen3utils",
    license="Apache",
    packages=find_packages(),
    include_package_data=True,  # include non-code files from MANIFEST.in
    install_requires=[
        "PyYAML~=5.1",
        "click",
        "cdislogging~=1.0.0",
        "dictionaryutils~=3.0.0",
        "gen3datamodel~=3.0.0",
        "gen3dictionary~=2.0.1",
        "gen3git~=0.2.3",
        "packaging~=20.0",
        "psqlgraph~=3.0.0",
    ],
    entry_points={"console_scripts": ["gen3utils=gen3utils.main:main"]},
)
