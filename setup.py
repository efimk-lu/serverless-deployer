from setuptools import setup, find_packages

setup(
    name="serverless_deployer",
    version="0.0.1",
    packages=find_packages(exclude=["scripts", "configuration_examples", "tests*"]),
    include_package_data=True,
    python_requires=">=3.6",
    install_requires=["Click", "GitPython", "pyyaml"],
    entry_points={"console_scripts": ["sdeployer=serverless_deployer.sdeployer:cli"]},
)
