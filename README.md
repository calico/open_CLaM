# open_CLaM
open-source version of <ins>**C**</ins>alico <ins>**L**</ins>ipidomics <ins>**a**</ins>nd <ins>**M**</ins>etabolomics pipeline and data analysis tools.

# Description

open_CLaM is a code library and pipeline for processing metabolomic and lipidomics data.
The code can be accessed via linked sub-repositories.

# Pipeline Installation

to run `open_CLaM` as a fully functional pipeline, all of the component pieces should be installed and configured properly.

1. **Clone this repository**

The easiest way to get everything to work is to clone this entire repository to your computer,
including all submodules.

This will preserve the file structure of various pipeline components.
To do this, you may need to setup a github account, and/or create ssh keys.
Please follow instructions available elsewhere to help you in cloning this repository
to your computer.

Here is the command to clone this `open_CLaM` and all submodules to your computer:

```
git clone --recurse-submodules -j8 https://github.com/calico/open_CLaM.git
```

2. **C++ executables**

`open_CLaM` depends on several executables written in C++ using the Qt framework.
These may be built [from source](https://github.com/eugenemel/maven).  If you have
successfully cloned this entire repository and all subrepositories, the source files necessary to create these executables will be downloaded to your computer.
In order to build these executables, you will need to download and install `Qt`, `llvm`, and `boost`.
Specifically, this project calls for the `qmake` tool within `Qt`.
Installing and configuring `qmake` and `llvm` is the most difficult part of this installation.
Check out the [Qt website](https://www.qt.io/download) and [llvm website](https://llvm.org/) for helpful tips.
Once you have these installed, you may carry out the following commands:
```
cd <open_CLaM_dir>/maven
qmake build_no_gui.pro
make -Bj16
```
Where `<open_CLaM_dir>` is the directory where you have cloned the `open_CLaM` repository on your computer.
If this works properly, you should find the following two executable files:
```
<open_CLaM_dir>/maven/src/maven/bin/peakdetector
<open_CLaM_dir>/maven/src/maven_core/bin/mzDeltas
```
Which are used by the `open_ClaM` pipeline.

3. **R packages**

`open_CLaM` requires installation of additional R packages: [clamr](https://github.com/calico/clamr), [clamdb](https://github.com/calico/clamdb), [clamqc](https://github.com/calico/clamqc), and [quahog](https://github.com/calico/quahog).
These repositories are all sub-repositories to `open_CLaM`.
Please follow the installation instructions associated with each repo.
Note that these R packages will likely require installation additional CRAN dependencies.
Note that `clamr` is a required dependency of `clamdb`, `clamqc`, and `quahog`, and so
should be installed first.

R packages can be installed by either (1) following the installation instructions described
in each repository, running (2) `R CMD INSTALL` for each package, e.g.
```
cd <open_CLaM_dir>
R CMD INSTALL clamr
R CMD INSTALL clamdb
R CMD INSTALL clamqc
R CMD INSTALL quahog
```
Or, (3) by building each package from source in the R studio console, e.g.
```
install.packages("<open_CLaM_dir>/clamr", repos=NULL, type ="source")
install.packages("<open_CLaM_dir>/clamdb", repos=NULL, type ="source")
install.packages("<open_CLaM_dir>/clamqc", repos=NULL, type ="source")
install.packages("<open_CLaM_dir>/quahog", repos=NULL, type ="source")
```

# Pipeline execution
The pipeline should be executed using the associated python scripts included
in this repository.  Python 3 is required.

Please follow the steps in the [open_CLaM_pipeline_example](https://github.com/calico/open_CLaM/tree/main/open_CLaM_example) for a detailed tutorial.