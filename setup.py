from setuptools import setup, find_packages

setup(
    name="backlooms",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "anthropic",
        "fastapi",
        "sqlalchemy",
        "setuptools",
        "python-dotenv",
        "mysql-connector-python",
        "uvicorn"
    ]
)
