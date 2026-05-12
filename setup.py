from setuptools import setup, find_packages
setup(
    name="ezpaw",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "gpaw",
        "ase",
        "psycopg2-binary",
        "python-dotenv",
        "pyyaml",
        "flask",
    ],
    entry_points={
        "console_scripts": [
            "ezpaw=ezpaw.cli:main",
        ],
    },
    python_requires=">=3.10",
)