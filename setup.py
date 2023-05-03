import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pylift",
    author_email="sylvain.loiseau@univ-paris13.fr",
    author="Sylvain Loiseau",
    version="0.0.1",
    description="Utilities for the LIFT lexicon format (Lexicon interchange format)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.univ-paris13.fr/sylvain.loiseau/pylift",
    project_urls={
        "Bug Tracker": "https://gitlab.univ-paris13.fr/sylvain.loiseau/pylift",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"pylift": "src"},
    package_data={"pylift": ["py.typed", 'src/schema']},
    include_package_data=True,
    packages=["pylift"],
    #packages=setuptools.find_packages(where="src"),
    install_requires=[
          'lxml>=4.6.3',
          'pytest>=6.2.5',
          'pycldf>=1.34.1',
          'cldfbench>=1.13.0',
          'pandas>=1.3.5'
    ],
    python_requires=">=3.7",
    entry_points = {
        'console_scripts': ['liftlex=pylift.cli:liftlex']
    }
)

