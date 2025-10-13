from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="analyze-chess",
    version="1.1.2",
    author="AprilLorDrake",
    author_email="your-email@example.com",
    description="A comprehensive chess position analysis tool using Stockfish engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/AprilLorDrake/Analyze_Chess",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment :: Board Games",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "analyze-chess=app:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["assets/*", "bin/*", "*.bat", "*.ps1"],
    },
)
