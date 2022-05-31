#! /usr/bin/env python3

import sys

if sys.version_info[0] < 3:
    raise Exception("Mzkit must be run with Python 3")

import os
import traceback

from collections import OrderedDict

from classes import *

# set global permissions for created folders
os.umask(0o02)

if __name__ == '__main__':
    
    args = mzkit_commandline_parser().parse_args()
    
    # set up run paths
    settings = MzkitSettings(args)
    
    # read and process config file
    try:
        config_path = args.configfile
        config = MzkitConfig(args.configfile)
    except Exception as e:
        print(e)
        print("Configuration file missing or unreadable - Exiting program.")
        exit(1)

    # overwrite config with wild cards specifications
    config.update_config(args.wild_cards)

    # save config
    config.write_config(os.path.join(settings.run['output_folder'], 'config.json'))
    
    # print a summary of the pipeline pipes (steps)
    config.print_pipeline_summary()
    
    #run_pipe(config, settings, "coelution")
    pipeline_status_dict = OrderedDict()

    method_id = config.globals['methodId']

    try:
        print("=================================================")
        print("mzkit_v2.py CONFIG PARAMETERS:")
        print("use config pipeline search? " + str(config.pipeline['search']['use']))
        print("method id? " + str(method_id))
        print("matching model? " + str(config.modules['pipeline_standard_search']['parameters']['matching_model']))

        print("use config pipeline search? " + str(config.pipeline['search']['use'] is True))
        print("method id is lipid search? " + str((method_id == 'M004A' or method_id == 'M005A')))
        print("pipeline search is peakdetector_mzkitchen_search? " + str(
            config.modules['pipeline_standard_search']['parameters']['matching_model'] == 'peakdetector_mzkitchen_search'))
        print("=================================================")
    except KeyError:
        print("mzkit_v2.py CONFIG PARAMETERS missing one or more keys.")

    for pipe in config.pipeline.keys():
        try:

            # iterate through steps in the pipeline
            pipe_status_dict = run_pipe(config, settings, pipe)
        
            if pipe_status_dict['status']['critical_fail']:
                print('pipeline stage \"' + pipe + '\" experienced a critical failure. Halting execution.')
                print('ERROR')
                exit(1)

        except ValueError as e:
            print("Unexpected ValueError occurred while executing mzkit pipeline. Halting execution.")
            print('ERROR')
            print(traceback.format_exception(None,  # <- type(e) by docs, but ignored
                                             e, e.__traceback__),
                  file=sys.stderr, flush=True)
            exit(1)

        except RuntimeError as e:
            print("Unexpected runtime error occurred while executing mzkit pipeline. Halting execution.")
            print('ERROR')
            print(traceback.format_exception(None,  # <- type(e) by docs, but ignored
                                             e, e.__traceback__),
                  file=sys.stderr, flush=True)
            exit(1)
        
        pipeline_status_dict[pipe] = pipe_status_dict
    
    create_success_file(pipeline_status_dict, settings)
    exit(0)
