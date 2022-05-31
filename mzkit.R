# mzkit.R is an Rscript that is meant to be run from mzkit.py and will
# run one of a set of pipeline wrappers using a functional approach where a function name
# and arguments are passed

library(quahog)
test_quahog_packages()

Sys.umask("000")
future::plan("multicore") # run jobs with multiple cores if available and multiple background R sessions otherwise

# format arguments

# read in command line arguments
input_args <- commandArgs()
formatted_flags <- format_flagged_arguments(input_args)

# pull out arguments which are required for all r wrappers
if (!("rwrapper" %in% names(formatted_flags))) {
  stop("rwrapper must be included as an input flag: rwrapper=value")
} else {
  rwrapper <- unname(formatted_flags['rwrapper'])
}

if (!("r_scripts_path" %in% names(formatted_flags))) {
  stop("r_scripts_path must be included as an input flag: r_scripts_path=value")
} else {
  r_scripts_path <- unname(formatted_flags['r_scripts_path'])
}

# disable debugging / console warnings
debugr::debugr_switchOff()
options(warn=-1)

# loading pipeline wrappers
test_rwrapper()

result <- tryCatch({
  do.call(rwrapper, as.list(formatted_flags))
}, error = function(err) {
  message("\nconfig:")
  message(paste(paste0(names(formatted_flags), ":", unname(formatted_flags)), collapse = "\n"))
  message("\nerror:")
  message(err)
  quit(status=1)
})
