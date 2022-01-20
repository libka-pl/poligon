from setuptools import setup, find_packages

try:
    import kolang
except ModuleNotFoundError:
    # Dependecies not installed yet
    import ast
    kolang = type('PseudoModule', (), {
        '__version__': '0.0.1',
        '__author__': 'unknown'
    })()
    with open('kolang/__init__.py') as f:
        for line in f:
            if line.strip().startswith('__version__'):
                kolang.__version__ = ast.parse(line).body[0].value.s
            elif line.strip().startswith('__author__'):
                kolang.__author__ = ast.parse(line).body[0].value.s

setup(
    name="kolang",
    description="Kodi language tool",
    version=kolang.__version__,
    author="Robert Kalinowski",
    author_email="robert.kalinowski@sharkbits.com",
    packages=find_packages(),
    platforms="any",
    python_requires='>=3.8',
    license='MIT',
    install_requires=[
        "polib==1.1.1",
    ],
    entry_points={
        "console_scripts": [
            "kolang=kolang:main",
        ]
    },
)
