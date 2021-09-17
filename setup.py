import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="zszia_solnlib",
    version="0.0.1",
    author="zep",
    author_email="xxx@example.com",
    description="Splunk solnlib",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=[
        "splunk-sdk",
    ],
    url="https://github.com/zszia/addonfactory-solutions-library-python.git",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
