"""Setup script for Cascade CLI."""

from setuptools import find_packages, setup

setup(
    name="cascade-cli",
    version="3.7.2",
    description="A terminal-based AI coding assistant inspired by Windsurf/Cascade",
    author="Cascade Team",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.27.0",
        "rich>=13.0.0",
    ],
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "cascade=cascade.main:main",
            "troya=cascade.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Tools",
    ],
)
