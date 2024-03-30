from setuptools import setup


setup(
    name="extracontext",
    author="Joao S. O. Bueno",
    description="Context Variable namespaces supporting generators, asyncio and multi-threading",
    packages=["extracontext"],
    long_description = open("README.md").read(),
    version="0.2beta2",
    install_requires=[],
    extras_require={
        "dev": ["pytest", "ipython", "black", "pyflakes", "mypy", "pytest-coverage"]
    },
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
    ],
)

