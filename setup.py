from setuptools import setup, find_packages

setup(
    name="sharedb-ot-client",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        'asyncio',
        'quill-delta',
        'websockets==11.*',
        'loguru'
    ]
)
