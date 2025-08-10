#!/usr/bin/env python3
"""
Setup script for AI Story Writer - Refactored Version
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_path = Path(__file__).parent.parent / "README.md"
long_description = ""
if readme_path.exists():
    with open(readme_path, "r", encoding="utf-8") as f:
        long_description = f.read()

# Read requirements
requirements_path = Path(__file__).parent.parent / "requirements_refactored.txt"
requirements = []
if requirements_path.exists():
    with open(requirements_path, "r", encoding="utf-8") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="ai-story-writer-refactored",
    version="2.0.0",
    description="AI Story Writer - Refactored version with clean architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AI Story Writer Team",
    author_email="",
    url="https://github.com/datacrystals/AIStoryWriter",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ai-story-writer=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Affero General Public License v3",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing :: Linguistic",
    ],
    keywords="ai story generation writing novel",
    project_urls={
        "Bug Reports": "https://github.com/datacrystals/AIStoryWriter/issues",
        "Source": "https://github.com/datacrystals/AIStoryWriter",
        "Documentation": "https://github.com/datacrystals/AIStoryWriter#readme",
    },
) 