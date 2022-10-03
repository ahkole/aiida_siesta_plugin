from aiida.engine import ToContext, WorkChain
from .base import SiestaBaseWorkChain, validate_options
from ..calculations.siesta import validate_parameters, validate_bandskpoints
from aiida import orm
from ..utils.tkdict import FDFDict


def validate_bdg_parameters(value, dummy):
    """
    Validate bdg_parameters input port'

    Validates the regular parameters. And that some forbidden
    Nambu flags are not used.
    """
    validate_parameters(value, dummy)
    if value:
        input_params = FDFDict(value.get_dict())
        for key in input_params:
            if key == FDFDict.translate_key("Nambu.ChemPot"):
                return "Can't manually set chemical potential, this is done automatically by the WorkChain"


class SiestaBdGSimpleWorkChain(WorkChain):
    """Workchain to perform a simple BdG calculation by concatenating a spin-orbit and a Nambu calculation"""

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(
            SiestaBaseWorkChain,
            exclude=('metadata', 'parameters', 'bandskpoints', 'options', 'settings',)
        )
        spec.input_namespace('soc', help='soc specific input', required=True)
        spec.input('soc.parameters', valid_type=orm.Dict, validator=validate_parameters)
        spec.input(
            'soc.bandskpoints',
            valid_type=orm.KpointsData,
            help='Input kpoints for bands',
            required=False,
            validator=validate_bandskpoints
        )
        spec.input('soc.options', valid_type=orm.Dict, validator=validate_options)
        spec.input('soc.settings', valid_type=orm.Dict, help='Input settings', required=False)
        spec.input_namespace('bdg', help='bdg specific input', required=True)
        spec.input('bdg.parameters', valid_type=orm.Dict, validator=validate_bdg_parameters)
        spec.input(
            'bdg.bandskpoints',
            valid_type=orm.KpointsData,
            help='Input kpoints for bands',
            required=False,
            validator=validate_bandskpoints
        )
        spec.input('bdg.options', valid_type=orm.Dict, validator=validate_options)
        spec.input('bdg.settings', valid_type=orm.Dict, help='Input settings', required=False)

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
        parameters = FDFDict(self.inputs.soc.parameters.get_dict())
        parameters['Spin'] = 'spin-orbit'   # Make sure spin is set to spin-orbit
        self.ctx.inputs['parameters'] = orm.Dict(dict=parameters.get_dict())
        self.ctx.inputs['options'] = self.inputs.soc.options
        if 'bandskpoints' in self.inputs.soc:
            self.ctx.inputs['bandskpoints'] = self.inputs.soc.bandskpoints
        if 'settings' in self.inputs.soc:
            self.ctx.inputs['settings'] = self.inputs.soc.settings
        self.ctx.inputs['clean_workdir'] = orm.Bool(False)  # Make sure we're not cleaning workdir

    def run_soc(self):
        self.report("Running SOC calculation")
        future = self.submit(SiestaBaseWorkChain, **self.ctx.inputs)

        return ToContext(soc_run=future)

    def prepare_bdg_input(self):
        self.report("Collecting Fermi energy from SOC run and preparing BdG inputs")

        Ef = self.ctx.soc_run.outputs.output_parameters['E_Fermi']
        self.ctx.inputs = self.exposed_inputs(SiestaBaseWorkChain)
        parameters = FDFDict(self.inputs.bdg.parameters.get_dict())
        parameters['Spin'] = 'Nambu'
        parameters['Nambu.ChemPot'] = '{0:.6f} eV'.format(Ef)
        parameters['DM.Normalization.Tolerance'] =  '1.D-1'  # Needed because Ef not updated during BdG
        self.ctx.inputs['parameters'] = orm.Dict(dict=parameters.get_dict())
        self.ctx.inputs['ions'] = self.ctx.soc_run.outputs.ion_files
        self.ctx.inputs['parent_calc_folder'] = self.ctx.soc_run.outputs.remote_folder
        self.ctx.inputs['options'] = self.inputs.bdg.options
        if 'bandskpoints' in self.inputs.bdg:
            self.ctx.inputs['bandskpoints'] = self.inputs.bdg.bandskpoints
        if 'settings' in self.inputs.bdg:
            self.ctx.inputs['settings'] = self.inputs.bdg.settings

    def run_bdg(self):
        self.report("Running BdG calculation")
        future = self.submit(SiestaBaseWorkChain, **self.ctx.inputs)

        return ToContext(bdg_run=future)

    def postprocess(self):
        """Here a higher level WorkChain could postprocess the results."""
