import json
import valideer
import os
import re
import argparse
from collections import OrderedDict
from datetime import datetime
import glob
from utils import *

class MzkitConfig(object):
    '''
    Summarizes steps of a metabolomics/lipidomics pipeline and the modules
    that will be utilized
    
    Attributes
    ----------
    json : dict
        the full .json configuration file
    pipeline : array
        sequence of steps to be called
    globals : dict
        parameters which will be available for all steps
    modules : dict
        module-specific parameters
    
    Methods
    -------
    get_pipe_dict(pipe: str)
        Generates pipe-specific config
    write_config(out_path: str)
        Write the config as a .json output
    update_config(updates: [str])
        Overwrite elements of the config
    '''    
    
    def __init__(self, 
                 config_path: str,
                ) -> None:
        '''
        Summarizes steps of a metabolomics/lipidomics pipeline and the modules
        that will be utilized
        
        Parameters
        ----------
        config_path : str
            path to a JSON config.
        
        Returns
        -------
        None.
        '''
        
        primary_config_schema = {
            "+pipeline": {},
            "+globals": {
                "+mzroll_db_file": "string",
                "+methodId": "string",
                "+chemical_class": "string",
                "+MS1tol": "string",
                "+MS2tol": "string",
                "+mode": "string",
                "+collision_energies": "string",
                "+dbname": "string",
                "+standard_db_user": "string",
                "+standard_db_passwd_key": "string",
                "+standard_db_host_key": "string"                
                },
            "+modules": {}
            }
        
        pipeline_config_schema = {
            "+use" : "boolean",
            "+required" : "boolean",
            "+critical" : "boolean",
            "+modules": ["string"]    
            }
        
        module_config_schema = {
            "+language" : "string",
            "+parameters" : {}    
            }
        
        primary_config_validator = valideer.parse(primary_config_schema)
        pipeline_config_validator = valideer.parse(pipeline_config_schema)
        module_config_validator = valideer.parse(module_config_schema)
        
        with open(config_path, 'r') as f:
            # check for primary fields
            self.config = json.load(f, object_pairs_hook=OrderedDict)
            # check high-level config organization
            primary_config_validator.validate(self.config)
            
            # check pipeline syntax
            for pipe in self.config['pipeline']:
                pipeline_config_validator.validate(self.config['pipeline'][pipe])
            
            # check module syntax
            for module in self.config['modules']:
                module_config_validator.validate(self.config['modules'][module])
            
            self.pipeline = self.config['pipeline']
            self.globals = self.config['globals']
            self.modules = self.config['modules']
            
        return
    
    def print_pipeline_summary(self) -> None:
        '''Prints a summary of the pipeline steps which will be run
        '''
        
        max_pipe_name_char = max([len(x) for x in self.pipeline.keys()])
        header_pad = " " * (max_pipe_name_char - 1)
        
        print("=================================================")
        print("PIPE" + header_pad + "USE\tREQ")
        
        for pipe in self.pipeline.keys():
            pipe_dict = self.pipeline[pipe]
            
            pipe_name_padding = " " * (max_pipe_name_char + 3 - len(pipe))
            
            print("%s" % pipe + pipe_name_padding + "%s\t%s" % (pipe_dict['use'], pipe_dict['required']))
        print("=================================================")
        
        return
            
    def get_pipe_dict(self, pipe: str) -> dict:
        '''Generates pipeline step (pipe) specific config
        
        Parameters
        ----------
        pipe : str
          pipe (pipeline step) for which to generate a configuration dict.
        
        Returns
        -------
        pipe_dict : dict
          pipeline steps and their associated parameters
        '''
        
        # check that pipe is defined in pipeline
        if pipe not in set(self.pipeline.keys()):
            raise ValueError('invalid step: %s is not defined in pipeline' %pipe)
        
        pipe_dict = OrderedDict()
        pipe_dict["pipe"] = self.pipeline[pipe]
        pipe_dict["modules"] = OrderedDict()
        
        if len(pipe_dict["pipe"]["modules"]) < 1:
           raise ValueError('invalid pipeline step: %s includes no modules' %pipe)
               
        # iterate through modules
        
        for module in pipe_dict["pipe"]["modules"]:
            if module not in set(self.modules.keys()):
                raise ValueError(' %s is an invalid pipeline step: {module} is not defined in modules' %pipe)
        
            module_dict = self.modules[module]
            module_dict['parameters'].update(self.globals)
            
            pipe_dict["modules"][module] = module_dict
        
        return pipe_dict
        
    def write_config(self, out_path: str) -> None:
    
        '''Write config to a file
        
        Parameters
        ----------
        out_path : str
          path to where .json config should be saved
        '''
    
        write_folder = os.path.abspath(os.path.join(out_path, os.pardir))
        if not os.path.exists(write_folder):
            raise ValueError('write path folder %s does not exist' %write_folder)
        
        if not out_path.endswith('.json'):
            raise ValueError('output file %s is not a .json file' %out_path)
        
        with open(out_path, 'w') as outfile:
            json.dump(self.config, outfile, indent = 4)
        
        
    def update_config(self, updates: [str]) -> None:
        
        '''Overwrite config with a set of value updates
        
        Parameters
        ----------
        updates : [str]
          list of values to overwrite: e.g., pipeline.search.use=false
        '''
        
        for update in updates:
            split_update = update.split('=', 1)
            print(split_update)
            
            # overwrite config dict position
            str_path = split_update[0].split('.')
            
            level_dicts = {}
            level = 0
            for level_str in str_path:
                level += 1
                # find parent dict
                if level == 1:
                    if not level_str in self.config.keys():
                        raise ValueError('%s is not a top-level config field' %level_str)
                    level_dict = self.config[level_str]
                else:
                    if not level_str in level_dicts[str_path[level-2]].keys():
                        raise ValueError('%s is not defined in current config' %level_str)
                    level_dict = level_dicts[str_path[level-2]][level_str]
                
                # check for level class
                if level == len(str_path):
                    if not type(level_dict) in [str, bool, float, int]:
                        raise ValueError('the terminal level of update path was a %s, classes must be one of str, bool, float or int' %type(level_dict))
                    else:
                        # update an entry
                        
                        # convert the value to an appropriate class
                        str_value = split_update[1]
                        if str_value in ["TRUE", "True", "true"]:
                            val = True
                        elif str_value in ["FALSE", "False", "false"]:
                            val = False
                        elif re.match('^[0-9e.]+$', str_value):
                            val = float(str_value)
                        else:
                            val = str_value
            
                        # save overwrittin value
                        level_dict = val
                        
                elif not isinstance(level_dict, dict):
                    raise ValueError('a level of update path - %s, was not a dict; only dict values can be updated' %type(level_dict))
                
                level_dicts[level_str] = level_dict
            
            level = len(level_dicts)
            while not level == 1:
                level -= 1
                str_level = str_path[level]
                update = level_dicts[str_level]
                level_dicts[str_path[level-1]][str_level] = update
            
            self.config[str_path[0]] = level_dicts[str_path[0]]
            
        self.write_config("/tmp/tmp.json")
        self = MzkitConfig("/tmp/tmp.json")
            
        return

    def configure_peakdetector_searches(self, settings):
        """Update peakdetector configurations

        The majority of the adjustments are made during json file generation.
        Here, only the msp file needs to be adjusted, based on its actual location in the docker container,
        instead of the path that is described in the json file.
        """
        if self.modules['pipeline_standard_search']['parameters']['matching_model'] != 'peakdetector_mzkitchen_search':
            return

        method_id = self.globals['methodId']
        msp_files = settings.program_settings['library_path'] + "/*" + method_id + "*.msp"

        files = glob.glob(msp_files)

        if len(files) >= 1:
            self.modules['peakdetector_mzkitchen_search']['parameters']['mzkitchenMspFile'] = files[0]
        else:
            print("Library path: " + settings.program_settings['library_path'])
            print("msp files: " + msp_files)
            raise MspFileMissingException("No msp file found for methodId: '" + method_id + "'. Halting execution.")
        return


class MzkitSettings(object):
    '''
    Bundle settings which will be used by the pipeline
    
    Attributes
    ----------
    project_files : [str]
        the full .json configuration file
    args : argparse.Namespace
        command-line arguments passed to pipeline
    program_settings : [str]
        paths to data, outputs and code
    run : dict
        timing, version, and reportion options
    
    '''

    def __init__(self, 
                 args: argparse.Namespace) -> None:
        '''
        Construct parameter set for run
        
        Parameters
        ----------
        args : argeparse.Namespace
            Command line arguments generated by argparse.
        
        Returns
        -------
        None.
        '''

        # program settings, unlikely to change between runs
        settings_program_schema = {
            "+open_CLaM_path": "string",
            "+peakdetector_bin_path": "string",
            "+peakdetector_methods_path": "string",
            "+mzdeltas_bin_path": "string",
            "+RCMD": "string",
            "r_scripts_path": "string",
            "r_mzkit_path": "string"
            }

        # run-specific parameters (changes every run)
        settings_run_schema = {
            "+data_folder": "string",
            "+output_folder": "string",
            "+configfile": "string",
            "+start_time": "datetime",
            "+verbose": "boolean"
            }

        data_folder = args.data_folder
        configfile = args.configfile
        output_folder = args.output_folder

        if data_folder is None:
            print("args.data_folder not provided: Falling back to open_CLaM example data_folder.")
            data_folder = os.path.abspath("./open_CLaM_example/example_data")

        if configfile is None:
            print("args.configfile not provided: Falling back to open_CLaM example configfile.")
            configfile = os.path.abspath("./open_CLaM_example/example_config.json")

        if output_folder is None:
            print("args.output_folder not provided: Falling back to open_CLaM example output folder.")
            output_folder = os.path.abspath("./open_CLaM_example/example_output")

        settings_program_validator = valideer.parse(settings_program_schema)
        settings_run_validator = valideer.parse(settings_run_schema)
        
        # test args formatting
        if not type(args) == argparse.Namespace:
            raise ValueError('args is of type %s rather than argparse.Namespace' % type(args))
        
        # sample files
        project_files = get_mz_files_list(data_folder)
        if len(project_files) == 0:
            raise ValueError("Didn't find any spectra files") 
        
        if any([str(x).endswith(".mzrollDB") for x in os.listdir(data_folder)]):
            raise ValueError("mzkit can't run on a data folder containing a .mzrollDB file") 
         
        output_folder = initialize_output_folder(output_folder)

        # open_CLaM program paths (executables, script directories, driver scripts)
        open_CLaM_path = os.path.abspath(".")
        peakdetector_bin_path = os.path.abspath("./maven/src/maven/bin")
        peakdetector_methods_path = os.path.abspath("./maven/src/maven_core/bin/methods")
        mzdeltas_bin_path = os.path.abspath("./maven/src/maven_core/bin")
        r_scripts_path = os.path.abspath(".")
        r_mzkit_path = os.path.abspath("./mzkit.R")

        # setup code paths
        settings_program = {
            "open_CLaM_path": open_CLaM_path,
            "peakdetector_bin_path": peakdetector_bin_path,
            "peakdetector_methods_path": peakdetector_methods_path,
            "mzdeltas_bin_path": mzdeltas_bin_path,
            "RCMD": "Rscript",
            "r_scripts_path": r_scripts_path,
            "r_mzkit_path": r_mzkit_path
            }
        
        settings_run = {
            "data_folder": data_folder,
            "output_folder": output_folder,
            "configfile": configfile,
            "start_time": datetime.now(),
            "verbose": args.verbose
            }

        self.project_files = project_files
        self.args = args
        self.mzrolldb_file = output_folder + "/peakdetector.mzrollDB"
        self.program_settings = settings_program_validator.validate(settings_program)
        self.run = settings_run_validator.validate(settings_run)

        return


