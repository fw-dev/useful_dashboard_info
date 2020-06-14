import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="filewave-extra-metrics", 
    version="1.0.0",
    author="John Clayton",
    author_email="johnc@filewave.com",
    description="An additional module that exposes s/ware patching and metrics information to the built in FileWave dashboard",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/johncclayton/useful_dashboard_info",
    packages=setuptools.find_packages(),
    include_package_data=True,
    entry_points = {
        'console_scripts': [
            'extra-metrics-install=extra_metrics.scripts:install_into_environment',
            'extra-metrics-run=extra_metrics.scripts:run_test_server',
        ]
    },
    install_requires=[
        'requests',
        'prometheus_client',
        'pandas',
        'PyYAML',
        'click',
        'progressbar2',
        'timeloop'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)