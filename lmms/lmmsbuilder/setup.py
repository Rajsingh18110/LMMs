from setuptools import setup, find_packages

setup(
    name="lmms-builder",
    version="1.0.0",
    description="Bootstrapper for the LMMs OS",
    packages=find_packages(),
    install_requires=[
        "psutil",
        "rich",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "LMMs-builder=lmms_builder.cli:builder_main",
            "LMMs-repair=lmms_builder.cli:repair_main",
            "LMMs-rebuild=lmms_builder.cli:rebuild_main",
            "LMMs-uninstall=lmms_builder.cli:uninstall_main",
            "LMMs-set=lmms_builder.cli:set_main",
            "LMMs=lmms_builder.cli:lmms_main",
            "LMMs-cl=lmms_builder.cli:cl_main",
        ]
    },
    python_requires=">=3.9",
    zip_safe=False,
)
