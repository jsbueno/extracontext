from setuptools import setup


setup(
    name="extracontext",
    author="Joao S. O. Bueno",
    description="All terrain context variable support",
    version="0.1",
    install_requires=[],
    extras_require={
        "dev": ["pytest", "ipython", "black", "pyflakes", "mypy", "pytest-coverage"]
    },
    classifiers = [
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
        "Operating System :: OS Independent",
    ],
)

