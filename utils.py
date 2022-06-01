import os
import subprocess
import platform
import argparse
from collections import OrderedDict
from pytz import timezone
import os
import re
from time import time, gmtime, strftime
from datetime import datetime


class PipelineFailedException(Exception):
    pass


class MspFileMissingException(Exception):
    pass


def get_mz_files_list(project_folder):
    matched = []

    spectra_files = re.compile('\.[mzXML|mgf|mzML]', flags=re.I)
    for root, sub_dirs, files in os.walk(project_folder):
        for b_name in files:
            if re.search(spectra_files, b_name):
                matched.append(root + "/" + b_name)

    if len(matched) == 0:
        print("Could not find any spectra files in " + project_folder + "/")

    print("# Found ", len(matched), " mass spec samples")
    return matched


def get_elapsed_time(start_time, end_time):
    time_elapsed = end_time - start_time

    hours, remainder = divmod(time_elapsed.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_elapsed_str = '{:03}hr {:02}m {:02}s'.format(int(hours), int(minutes), int(seconds))

    return time_elapsed_str


def exit_with_error(err_str):
    raise NameError("ERROR: " + err_str)


def mzkit_commandline_parser():
    
    parser = argparse.ArgumentParser(description="Primary entry point for mass spec pipeline",
                                     usage="python mzkit.py -d=MZXMLFOLDER [-r regexp] [-t maxmodtime] [-o output_folder] [-c configfile]")

    parser.add_argument('-d', '--data_folder',
                        help='data folder',
                        dest='data_folder',
                        required=True)

    parser.add_argument('-c', '--config',
                        help='configuration file',
                        dest='configfile',
                        default=None)

    parser.add_argument('-r', '--include',
                        help='regexp subset of samples to include in analysis',
                        dest='include_pattern',
                        default=None)

    parser.add_argument('-t', '--maxModTime',
                        help='include only files that have been modified in last \
                        t hours',
                        dest='maxModTime',
                        default=1000000000000)

    parser.add_argument('-o', '--output_folder',
                        help='output folder',
                        dest='output_folder',
                        default=None)

    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        help='enable verbose mode',
                        choices=[True, False],
                        default=True)

    parser.add_argument('-w', "--wild-cards",
                        dest='wild_cards',
                        help = "Used to overwrite config arguments",
                        nargs='*',
                        default=[])

    '''
    --wild-cards argument with
    "--wild-cards" "modules.pipeline_qc.parameters.referenceSample=<referenceSample>
    '''

    return parser


def run_pipe(config, settings, pipe):
  
    '''
    Run one step of the pipeline
    
    run_pipe() runs one step of a pipeline (a pipe) which may encompass
    multiple modules. modules are used for their side effects.
        
    Parameters
    ----------
    config : dict
      configuration generated using mzkitConfig()
    settings: dict
      paths to the dataset, outputs and programming assets, and run settings
    pipe : str
      name of the pipe to run.
        
    Returns
    -------
    status_dict : dict
      pipeline steps and their associated parameters
    '''
  
    pipe_config = config.get_pipe_dict(pipe)
    
    use = pipe_config['pipe']['use'] # should the step be run
    required = pipe_config['pipe']['required'] # should a failure stop the pipeline. this could be altered if a certain non-critical step is required for an analysis (e.g.,)
    critical = pipe_config['pipe']['critical'] # does a pipe always need to be run
    modules_dict = pipe_config['modules']
    
    if critical and not use:
        raise ValueError('the %s pipe is set to not be used, but this pipe is critical' %pipe)
    
    if required and not use:
        raise ValueError('the %s pipe is set to not be used, but this pipe is required' %pipe)
    
    if critical and not required:
        raise ValueError('the %s pipe is set to as critical but not required; all critical steps are required' %pipe)
    
    status_dict = {}
    timing_dict = OrderedDict()
    step_start = datetime.now()
    
    print("=================================================")
    print("#### Running Pipe: " + pipe)
    
    if use:
        fail = False
        for module in pipe_config['pipe']['modules']:
          
            print("    =>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=>=")
            print("    #### Running Module: " + module)
            print("    \n")

            # determine whether previous steps have failed        
            if not fail:
                try:
                    # run module
                    run_module(module, modules_dict[module], pipe, settings)
                    fail = False
                    message = "success"

                except PipelineFailedException:
                    print("    \n")
                    print("    #### Caught PipelineFailedException in module: " + module)
                    fail = True
                    message = "failure of non-critical module"

        
            # save timing information
            timing_dict[module] = {
                'end_time': datetime.now(),
                'message': message
                }
    
        status_dict['timing_dict'] = timing_dict
        status_dict['status'] = {
            'ran': True,
            'critical_fail': ((fail and critical) or (fail and required)),
            'fail': fail
            }
    else:
        # pipe not run, but still return a status_dict
      
        for module in pipe_config['pipe']['modules']:
            timing_dict[module] = {
                'end_time': datetime.now(),
                'message': "Not run"
                }
        
        status_dict['timing_dict'] = timing_dict
        status_dict['status'] = {
            'ran': False,
            'critical_fail': False,
            'fail': False
            }

    print("    ")
    print("    #### Completed Pipe: " + pipe + " in " + get_elapsed_time(step_start, datetime.now()))
    print("    =============================================\n")

    return status_dict
    
    
def run_module(module, module_dict, pipe, settings):
  
    # call module
    
    language = module_dict['language']
    
    if language == "bin":
        summary_dict = call_bin_module(module, module_dict, pipe, settings)
    elif language == "R":
        summary_dict = call_R_module(module, module_dict, settings)
    else:
        raise ValueError('invalid language: %s does not have a defined calling method' %language)
        
    return summary_dict
  

def call_R_module(module, module_dict, settings):

    output_path_argument = "output_folder={}".format(settings.run['output_folder'])
    function_call_argument = "rwrapper={}".format(module)
    r_scripts_path_argument = "r_scripts_path={}".format(settings.program_settings['r_scripts_path'])

    aux_r_params = []
    for par, val in module_dict['parameters'].items(): 
        aux_r_params.append(par + "=" + str(val))
    #print(aux_r_params)

    cmd = [settings.program_settings['RCMD'],
           settings.program_settings['r_mzkit_path'],
           output_path_argument,
           function_call_argument,
           r_scripts_path_argument] + aux_r_params
           
    p = subprocess.Popen(" ".join(cmd),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True,
                         close_fds=True)

    out, err = p.communicate()

    # decode byte string
    out = out.decode("utf-8")

    if settings.run['verbose']:
        print(out)
    if p.returncode != 0:

        err = err.decode("utf-8")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("ERROR")
        print(err)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        raise(PipelineFailedException(err))


def call_bin_module(module, module_dict, pipe, settings):
    
    if module == "peakdetector" or module == "peakdetector_mzkitchen_search":
        if pipe == "peakdetector":
            run_peakdetector(settings.args.data_folder, module_dict, settings)  # throws PipelineFailedException
        elif pipe == "alignment":
            run_peakdetector(settings.mzrolldb_file, module_dict, settings)  # throws PipelineFailedException
        else:
            raise ValueError("Called peakdetector from undefined pipe: %s" % pipe)
    elif module == "mz_deltas":
        run_mzdeltas(module_dict, settings)  # throws PipelineFailedException
    else:
        raise ValueError("%s doesn't have a defined method for calling the appropriate binary" % module)
      
    return


def run_peakdetector(peakdetector_input, module_dict, settings):

    peakdetector_binary = settings.program_settings['peakdetector_bin_path'] + '/peakdetector'

    # On Mac os x, executable is located inside the peakdetector.app folder
    if platform.system() == "Darwin" and not os.path.exists(peakdetector_binary):
        peakdetector_binary = settings.program_settings['peakdetector_bin_path'] + "/peakdetector.app/Contents/MacOS/peakdetector"

    if not os.path.exists(peakdetector_binary):
        raise ValueError('Cannot find peakdetector binary: %s' %peakdetector_binary)
      
    if not os.path.exists(settings.program_settings['peakdetector_methods_path']):
        raise ValueError('Cannot find peakdetector methods folder: %s' % settings.program_settings["peakdetector_methods_path"])

    align_samples_flag = module_dict['parameters']['alignSamples']
    if peakdetector_input.endswith(".mzrollDB"):
        align_samples_flag = 0

    # Additional peakdetector options

    # mz slices
    rtStepSize = 10   # scans
    precursorPPM = 5  # for mz slice

    # grouping (and peak picking)
    eic_smoothingWindow = 5  # scans (Gaussian smoothing, # scans with >= 50% amplitude)
    baseline_smoothingWindow = 5  # scans (Gaussian smoothing, # scans with >= 50% amplitude)
    baseline_dropTopX = 60  # intensity percentile below which to consider baseline in slice
    grouping_maxRtWindow = 0.5  # minutes (max RT distance between sample peak RT and merged EIC peak RT)

    # group cleaning and filtering
    minGoodGroupCount = 1   # "good" by peakdetector default.model
    minQuality = 0.5   # minimum peak quality for peak to be "good"
    minSignalBaseLineRatio = 5   # largest peak intensity : peak baseline, peak baseline @ bounds or max
    mergeOverlap = 0.8  # %RT overlap, for merging peak groups with similar RTs

    # Generalized mzkitchen msp search
    mzKitchenSearchType = ""
    mzKitchenMspFile = ""
    mzKitchenSearchParameters = ""

    if 'rtStepSize' in module_dict['parameters']:
        rtStepSize = module_dict['parameters']['rtStepSize']

    if 'precursorPPM' in module_dict['parameters']:
        precursorPPM = module_dict['parameters']['precursorPPM']

    if 'eic_smoothingWindow' in module_dict['parameters']:
        eic_smoothingWindow = module_dict['parameters']['eic_smoothingWindow']

    if 'baseline_smoothingWindow' in module_dict['parameters']:
        baseline_smoothingWindow = module_dict['parameters']['baseline_smoothingWindow']

    if 'baseline_dropTopX' in module_dict['parameters']:
        baseline_dropTopX = module_dict['parameters']['baseline_dropTopX']

    if 'grouping_maxRtWindow' in module_dict['parameters']:
        grouping_maxRtWindow = module_dict['parameters']['grouping_maxRtWindow']

    if 'minGoodGroupCount' in module_dict['parameters']:
        minGoodGroupCount = module_dict['parameters']['minGoodGroupCount']

    if 'minQuality' in module_dict['parameters']:
        minQuality = module_dict['parameters']['minQuality']

    if 'minSignalBaseLineRatio' in module_dict['parameters']:
        minSignalBaseLineRatio = module_dict['parameters']['minSignalBaseLineRatio']

    if 'mergeOverlap' in module_dict['parameters']:
        mergeOverlap = module_dict['parameters']['mergeOverlap']

    if 'mzkitchenSearchType' in module_dict['parameters']:
        mzKitchenSearchType = module_dict['parameters']['mzkitchenSearchType']
        mzKitchenMspFile = module_dict['parameters']['mzkitchenMspFile']
        mzKitchenSearchParameters = module_dict['parameters']['mzkitchenSearchParameters']

    cmd_str = "{peakdetector_binary} {ms2} \
                                     -i{minintensity} \
                                     -m{peakdetector_methods_path} \
                                     -o{reports_folder} \
                                     -a{align_samples} \
                                     -r{mzSlice_rtStepSize} \
                                     -p{mzSlice_precursorPPM} \
                                     -y{grouping_eic_smoothingWindow} \
                                     -7{grouping_baseline_smoothingWindow} \
                                     -8{grouping_baseline_dropTopX} \
                                     -g{grouping_maxRtWindow} \
                                     -b{cleaning_minGoodGroupCount} \
                                     -q{cleaning_minQuality} \
                                     -z{cleaning_minSignalBaseLineRatio} \
                                     -u{cleaning_mergeOverlap} \
                                     ".format(peakdetector_binary=peakdetector_binary,
                                              ms2=module_dict['parameters']['ms2'],
                                              minintensity=module_dict['parameters']['minintensity'],
                                              peakdetector_methods_path=settings.program_settings['peakdetector_methods_path'],
                                              reports_folder=settings.run['output_folder'],
                                              align_samples=align_samples_flag,
                                              mzSlice_rtStepSize=rtStepSize,
                                              mzSlice_precursorPPM=precursorPPM,
                                              grouping_eic_smoothingWindow=eic_smoothingWindow,
                                              grouping_baseline_smoothingWindow=baseline_smoothingWindow,
                                              grouping_baseline_dropTopX=baseline_dropTopX,
                                              grouping_maxRtWindow=grouping_maxRtWindow,
                                              cleaning_minGoodGroupCount=minGoodGroupCount,
                                              cleaning_minQuality=minQuality,
                                              cleaning_minSignalBaseLineRatio=minSignalBaseLineRatio,
                                              cleaning_mergeOverlap=mergeOverlap
                                              )

    # Generalized mzkitchen msp search
    if mzKitchenSearchType:
        cmd_str = cmd_str + "-0" + mzKitchenSearchType + " "
        if mzKitchenMspFile:
            cmd_str = cmd_str + "-1" + mzKitchenMspFile + " "
            if mzKitchenSearchParameters:
                cmd_str = cmd_str + "-9" + mzKitchenSearchParameters + " "

    # Pass in whole directory instead of list of files
    if not peakdetector_input.endswith(".mzrollDB") and not peakdetector_input.endswith("/"):
        peakdetector_input = peakdetector_input + "/"

    cmd_str = cmd_str + " " + peakdetector_input

    # Include alignment file
    if module_dict['parameters']['alignmentFile']:
        cmd_str = cmd_str + " " + module_dict['parameters']['alignmentFile']

    print("#RUNNING ", cmd_str)

    p = subprocess.Popen(cmd_str,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True,
                         close_fds=True)

    out, err = p.communicate()

    # decode byte string
    out = out.decode("utf-8")

    if settings.run['verbose']:
        print(out)
    if p.returncode != 0:

        err = err.decode("utf-8")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("ERROR")
        print(err)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        raise PipelineFailedException(err)


def run_mzdeltas(module_dict, settings):
    
    if not os.path.exists(settings.program_settings['mzdeltas_bin_path']):
        raise ValueError("Can not find mzDeltas binary at %s" % settings.program_settings['mzdeltas_bin_path'])

    mzdeltas_binary = settings.program_settings['mzdeltas_bin_path'] + '/mzDeltas'
    # On Mac os x, executable is located inside the peakdetector.app folder
    if platform.system() == "Darwin" and not os.path.exists(mzdeltas_binary):
        mzdeltas_binary = settings.program_settings['mzdeltas_bin_path'] + "/mzDeltas.app/Contents/MacOS/mzDeltas"

    output_file = settings.run['output_folder'] + "/mzdeltas.out"

    cmd_str = "{mzdeltas_binary} --minintensity {minintensity} \
                                 --max_mzs {max_mzs} --ppm {ppm} \
                                 --mincor {mincor} --historylen {historylen} \
                                 --output {outputfile} \
                                  ".format(mzdeltas_binary=mzdeltas_binary,
                                           minintensity=module_dict['parameters']['minintensity'],
                                           max_mzs=module_dict['parameters']['max_mzs'],
                                           ppm=module_dict['parameters']['ppm'],
                                           mincor=module_dict['parameters']['mincor'],
                                           historylen=module_dict['parameters']['historylen'],
                                           outputfile=output_file)

    data_folder = settings.run['data_folder']
    if not data_folder.endswith("/"):
        data_folder = data_folder + "/"

    cmd_str = cmd_str + " " + data_folder

    print(cmd_str)
    p = subprocess.Popen(cmd_str,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True,
                         close_fds=True)

    out, err = p.communicate()

    # decode byte string
    out = out.decode("utf-8")

    if settings.run['verbose']:
        print(out)
    if p.returncode != 0:

        err = err.decode("utf-8")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("ERROR")
        print(err)
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        raise PipelineFailedException(err)

    if not os.path.isfile(output_file):
        raise OSError(2, "Outfile not found")


def create_success_file(pipeline_status_dict, settings):
    
    success_file = settings.run['output_folder'] + "/success.txt"
    start_time = settings.run['start_time']
    end_time = datetime.now()
    
    f = open(success_file, "w+")
    
    f.write("mzkit pipeline completed successfully!\r\n\r\n")

    total_time_elapsed = get_elapsed_time(start_time, end_time)

    f.write("Pipeline Performance:\r\n")
    f.write("Run started at:\r\n" + timezone('US/Pacific').localize(start_time).strftime('%m/%d/%Y %I:%M:%S %p PDT') + "\r\n\r\n")
    f.write("Run completed at:\r\n" + timezone('US/Pacific').localize(end_time).strftime('%m/%d/%Y %I:%M:%S %p PDT') + "\r\n\r\n")
    f.write("Total elapsed time:\r\n" + total_time_elapsed + "\r\n")
    f.write("\r\n")

    step_start = start_time
    for pipe in pipeline_status_dict:

        f.write("\r\n")
        f.write(pipe + " step: ")
    
        if not pipeline_status_dict[pipe]['status']['ran']:
            f.write("SKIPPED\r\n")
            continue
        elif pipeline_status_dict[pipe]['status']['fail']:
            f.write("FAILED :( check output\r\n")
        else:
            f.write("SUCCEEDED\r\n")
        
        timing_dict = pipeline_status_dict[pipe]['timing_dict']
        for module in timing_dict.keys():
            module_timing_dict = timing_dict[module]
        
            end_time = module_timing_dict['end_time']
            elapsed_time = get_elapsed_time(step_start, end_time)
            step_start = end_time
        
            # write out timing summary
            f.write(module + ": " + elapsed_time + " - " + module_timing_dict['message'] + "\r\n")

    f.write("\r\n")
    f.write("\r\n")

    f.close()

    print("=================================================")
    print("=================================================")
    print("# Completed pipeline in " + get_elapsed_time(start_time, end_time))
    print("=================================================")
    print("=================================================\n")


def initialize_output_folder(output_folder):

    if not os.path.exists(output_folder):
        print("# Creating " + output_folder)
        os.mkdir(output_folder)
        os.mkdir(os.path.join(output_folder, "QC"))
        os.mkdir(os.path.join(output_folder, "reports"))
        os.mkdir(os.path.join(output_folder, "libraries"))
        if not os.path.exists(output_folder):
            exit_with_error("Can't create output folder:", output_folder)
    else:
        qc_folder = os.path.join(output_folder, "QC")
        if not os.path.exists(qc_folder):
            os.mkdir(qc_folder)

        reports_folder = os.path.join(output_folder, "reports")
        if not os.path.exists(reports_folder):
            os.mkdir(reports_folder)

        libraries_folder = os.path.join(output_folder, "libraries")
        if not os.path.exists(libraries_folder):
            os.mkdir(libraries_folder)

    print("# Reports will saved to " + output_folder + " folder.")

    return output_folder
