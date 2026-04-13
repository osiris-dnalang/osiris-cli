from setuptools import setup, find_packages

setup(
    name="dnalang_sdk",
    version="0.1.0",
    description="DNALang SDK for OSIRIS integration",
    author="OSIRIS Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[],
    python_requires=">=3.8",
)