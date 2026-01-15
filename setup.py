# Sphinx Workflow Extension - Setup
# For installing the extension as a package

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / 'README.md'
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ''

setup(
    name='sphinx-workflow-ext',
    version='0.1.0',
    description='Sphinx extension for workflow protocol documentation',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Your Lab',
    author_email='your.email@example.com',
    url='https://github.com/yourusername/sphinx-workflow-ext',
    packages=find_packages(),
    package_data={
        'sphinx_workflow_ext': [
            'static/*.css',
            'static/*.js',
        ],
    },
    include_package_data=True,
    install_requires=[
        'sphinx>=4.0.0',
        'docutils>=0.17',
        'generate-workflow-docs>=1.0.0',  # Core workflow extraction library
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=3.0.0',
            'sphinx-rtd-theme>=1.0.0',
            'sphinxcontrib-mermaid>=0.7.0',
        ],
    },
    python_requires='>=3.8',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Documentation :: Sphinx',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    keywords='sphinx documentation workflow protocol',
)
