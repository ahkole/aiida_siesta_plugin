from aiida.engine import ToContext, WorkChain
from .base import SiestaBaseWorkChain, validate_options
from aiida import orm
from ..utils.tkdict import FDFDict


def validate_bdg_parameters(value, _):
    """
    Validate bdg_parameters input port'

    Checks that all input flags contain the Nambu keyword. And that some forbidden
    Nambu flags are not used.
    """
    if value:
        input_params = FDFDict(value.get_dict())
        for key in input_params:
            if key == FDFDict.translate_key("Nambu.ChemPot"):
                return "Can't manually set chemical potential, this is done automatically by the WorkChain"
            if not FDFDict.translate_key("Nambu") in key:
                return "Only parameters controlling the BdG calculation (containing Nambu) belong in the 'bdg_parameters'"


class SiestaBdGSimpleWorkChain(WorkChain):
    """Workchain to perform a simple BdG calculation by concatenating a spin-orbit and a Nambu calculation"""

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(SiestaBaseWorkChain, exclude=('metadata',))
        spec.input('bdg_parameters', required=True, valid_type=orm.Dict, validator=validate_bdg_parameters)
        spec.input('bdg_options', required=False, valid_type=orm.Dict, validator=validate_options)

        spec.outline(
            cls.prepare_soc_input,
            cls.run_soc,
            cls.prepare_bdg_input,
            cls.run_bdg,
            cls.postprocess,
        )

    def prepare_soc_input(self):
        self.report("Preparing inputs for SOC run")

        self.ctx.inputs = self.exposed_inputs(SiestaBaseWorkChain)
        parameters = FDFDict(self.ctx.inputs['parameters'].get_dict())
        parameters['Spin'] = 'spin-orbit'   # Make sure spin is set to spin-orbit
        self.ctx.inputs['parameters'] = orm.Dict(dict=parameters.get_dict())
        self.ctx.inputs['clean_workdir'] = orm.Bool(False)  # Make sure we're not cleaning workdir

    def run_soc(self):
        self.report("Running SOC calculation")
        future = self.submit(SiestaBaseWorkChain, **self.ctx.inputs)

        return ToContext(soc_run=future)

    def prepare_bdg_input(self):
        self.report("Collecting Fermi energy from SOC run and preparing BdG inputs")

        Ef = self.ctx.soc_run.outputs.output_parameters['E_Fermi']
        parameters = FDFDict(self.ctx.inputs['parameters'].get_dict())
        parameters['Spin'] = 'Nambu'
        parameters['Nambu.ChemPot'] = '{0:.6f} eV'.format(Ef)
        parameters['DM.Normalization.Tolerance'] =  '1.D-1'  # Needed because Ef not updated during BdG
        bdg_parameters = FDFDict(self.inputs.bdg_parameters.get_dict())
        # Add the BdG parameters
        for k, v in bdg_parameters.items():
            parameters[k] = v
        self.ctx.inputs['parameters'] = orm.Dict(dict=parameters.get_dict())
        self.ctx.inputs['ions'] = self.ctx.soc_run.outputs.ion_files
        self.ctx.inputs['parent_calc_folder'] = self.ctx.soc_run.outputs.remote_folder
        if 'bdg_options' in self.inputs:
            self.report("Input port 'bdg_options' present. Using this for BdG calculation")
            self.ctx.inputs['options'] = self.inputs.bdg_options

    def run_bdg(self):
        self.report("Running BdG calculation")
        future = self.submit(SiestaBaseWorkChain, **self.ctx.inputs)

        return ToContext(bdg_run=future)

    def postprocess(self):
        """Here a higher level WorkChain could postprocess the results."""
