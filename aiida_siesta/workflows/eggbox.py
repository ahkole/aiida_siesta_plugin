from aiida.engine import ToContext, WorkChain
from .base import SiestaBaseWorkChain
from .iterate import SiestaIterator
from aiida import orm
from ..utils.tkdict import FDFDict
import numpy as np


def is_correct_mask(mask, _):
    if len(mask) != 3:
        return 'The shift mask must contain exactly three numbers, one for each dimension'
    for i in mask:
        if not (np.isclose(0, i) or np.isclose(1, i)):
            return 'The shift mask must contain only zeroes or ones'


def is_positive_number_of_steps(n, _):
    if n <= 0:
        return 'The number of steps of the shift should be a positive number greater than zero'


def generate_shifts(cell, nx, ny, nz, nsteps, mask):
    shifts = []
    for i in range(1, nsteps+1):
        sx, sy, sz = mask[0]*i/(nx*nsteps)*cell[0,:] + mask[1]*i/(ny*nsteps)*cell[1,:] + mask[2]*i/(nz*nsteps)*cell[2,:]
        shifts.append("""
    {0:.8f} {1:.8f} {2:.8f}
%endblock AtomicCoordinatesOrigin""".format(sx, sy, sz))
    return shifts


class SiestaEggboxWorkChain(WorkChain):
    """Workchain to compute eggbox effect for SIESTA"""

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.expose_inputs(SiestaBaseWorkChain, exclude=('metadata',))
        spec.expose_inputs(SiestaIterator, include=('batch_size',))
        spec.input('shift_mask', required=False, default=lambda: orm.List(list=[1.,1.,1.])
                   , valid_type=(orm.List), validator=is_correct_mask)
        spec.input('shift_steps', required=False, default=lambda: orm.Int(10)
                   , valid_type=(orm.Int), validator=is_positive_number_of_steps)
        spec.outline(
            cls.prepare_base_input,
            cls.run_base,
            cls.prepare_iterate_input,
            cls.run_iterate,
            cls.postprocess,
        )

    def prepare_base_input(self):
        self.report("Preparing inputs for initial run for determining mesh")

        self.ctx.inputs = self.exposed_inputs(SiestaBaseWorkChain)
        parameters = FDFDict(self.ctx.inputs['parameters'].get_dict())
        parameters['%block AtomicCoordinatesOrigin'] = """
    0.0 0.0 0.0
%endblock AtomicCoordinatesOrigin"""
        self.ctx.inputs['parameters'] = orm.Dict(dict=parameters.get_dict())

    def run_base(self):
        self.report("Running initial run for determining mesh")
        future = self.submit(SiestaBaseWorkChain, **self.ctx.inputs)

        return ToContext(base_run=future)

    def prepare_iterate_input(self):
        self.report("Getting mesh from initial run and preparing input for shift iteration")

        nx, ny, nz = self.ctx.base_run.outputs.output_parameters['mesh']
        cell = np.array(self.ctx.base_run.inputs.structure.cell)
        self.ctx.iterate_over = {
            "%block AtomicCoordinatesOrigin": generate_shifts(cell=cell,
                                                              nx=nx,
                                                              ny=ny,
                                                              nz=nz,
                                                              nsteps=self.inputs.shift_steps.value,
                                                              mask=self.inputs.shift_mask.get_list(),)
        }

    def run_iterate(self):
        self.report("Iterating over shifts of the origin")
        future = self.submit(SiestaIterator,
                             **self.ctx.inputs,
                             **self.exposed_inputs(SiestaIterator),
                             iterate_over=self.ctx.iterate_over,
                             )
        return ToContext(iterate_run=future)

    def postprocess(self):
        """Here a higher level WorkChain could postprocess the results."""
