from distutils.core import setup

setup(
    name = "pynetlinux",
    version = "1.0",
    description = "Linux network configuration library for Python",
    author = "Roman Lisagor",
    author_email = "rlisagor+pynetlinux@gmail.com",
    url = "http://github.com/rlisagor/pynetlinux",
    license = "BSD",
    platforms = "Linux",
    packages = ["pynetlinux"],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: BSD License",
        "Operating System :: POSIX :: Linux",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration"
    ]
)
