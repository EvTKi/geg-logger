# setup.py
from setuptools import find_packages, setup

setup(
    name="geg-logger",  # Для pip установки (можно с дефисом)
    version="1.0.0",
    description="Переиспользуемый логгер для Python проектов",
    author="Your Name",
    packages=find_packages(),  # Найдет geg_logger папку
    package_dir={"": "."},  # Явно указываем корневую директорию
    python_requires=">=3.7",
    install_requires=[],
)
