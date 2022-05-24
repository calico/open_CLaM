# open_CLaM
open-source version of mass_spec

# Description

open_CLaM is a code library and pipeline for processing metabolomic and lipidomics data.
The code can be accessed via linked sub-repositories.

# Pipeline Installation

to run `open_CLaM` as a fully functional pipeline, all of the component pieces should be installed and configured properly.

1. *Clone this repository*

The easiest way to get everything to work is to clone this entire repository to your computer.
This will preserve the file structure of various pipeline components.
To do this, you may need to setup a github account, and/or create ssh keys.
Please follow instructions available elsewhere to help you in cloning this repository
to your computer.  You may also download the entire repository as a zipped file, and unzip
the complete directory locally.

2. *C++ executables*

`open_CLaM` depends on several executables written in C++ using the Qt framework.
These executables may be downloaded in finished form the [MAVEN Releases Page](https://github.com/eugenemel/maven/releases/latest).
They may also be built [from source](https://github.com/eugenemel/maven), if desired.
Once these executables have been obtained or built, please deposit them in the `executables`
sub-folder of your local copy of the `open_CLaM` pipeline.
The following executables should be copied to the `executables` folder:
```
peakdetector
mzDeltas
```

3. *R packages*

`open_CLaM` requires installation of additional R packages: [clamr](https://github.com/calico/clamr), [clamdb](https://github.com/calico/clamdb), [clamqc](https://github.com/calico/clamqc), and [quahog](https://github.com/calico/quahog).
These repositories are all sub-repositories to `open_CLaM`.
Please follow the installation instructions associated with each repo.
Note that these R packages will likely require installation additional CRAN dependencies.
Note that `clamr` is a required dependency of `clamdb`, `clamqc`, and `quahog`, and so
should be installed first.