from .iterate import SiestaIterator, set_up_parameters_dict
from .bdg_simple import SiestaBdGSimpleWorkChain


def set_up_parameters_dict_soc_bdg(val, inputs, parameter, input_key, defaults=None):
    """
    Parsing function that sets up an fdf parameter for the SOC or BdG run.
    """
    inputs_soc_bdg = getattr(inputs, input_key)
    val = set_up_parameters_dict(val, inputs_soc_bdg, parameter.split('-')[-1], input_key='parameters', defaults=defaults)
    inputs_soc_bdg['parameters'] = val

    return inputs_soc_bdg


def set_up_nested_soc_bdg(val, inputs, parameter, input_key):
    """
    Parsing function that sets up a nested input for the SOC or BdG run.
    """
    inputs_soc_bdg = getattr(inputs, input_key)
    inputs_soc_bdg[parameter.split('-')[-1]] = val

    return inputs_soc_bdg


_soc_keys = {}
_bdg_keys = {}
for k, v in SiestaIterator._params_lookup[-1]["keys"].items():
    _soc_keys['soc-parameters-' + k] = v
    _bdg_keys['bdg-parameters-' + k] = v


SIESTA_BDG_ITERATION_PARAMS = (
    *SiestaIterator._params_lookup[:(-1)],
    {
        "group_name":
        "FDF parameters SOC",
        "input_key":
        "soc",
        "help":
        """
        All the parameters that are used "raw" in the fdf file for the SOC run.

        WARNING: Even if the parameter does not make sense, if it has not been interpreted as belonging
        to any other group, it will be interpreted as an fdf parameter.
        """,
        "condition":
        lambda parameter: parameter.lower().startswith("soc-parameters"),
        "parse_func":
        set_up_parameters_dict_soc_bdg,
        "keys": _soc_keys
    }, {
        "group_name":
        "FDF parameters BdG",
        "input_key":
        "bdg",
        "help":
        """
        All the parameters that are used "raw" in the fdf file for the BdG run.

        WARNING: Even if the parameter does not make sense, if it has not been interpreted as belonging
        to any other group, it will be interpreted as an fdf parameter.
        """,
        "condition":
        lambda parameter: parameter.lower().startswith("bdg-parameters"),
        "parse_func":
        set_up_parameters_dict_soc_bdg,
        "keys": _bdg_keys
    }, {
        "group_name":
        "Nested input ports BdG",
        "input_key":
        "bdg",
        "help":
        """
        All the input ports that belong in the nested BdG input namespace.
        """,
        "condition":
        lambda parameter: parameter.lower().startswith("bdg"),
        "parse_func":
        set_up_nested_soc_bdg,
        "keys": {}
    }, {
        "group_name":
        "Nested input ports SOC",
        "input_key":
        "soc",
        "help":
        """
        All the input ports that belong in the nested BdG input namespace.
        """,
        "condition":
        lambda parameter: parameter.lower().startswith("soc"),
        "parse_func":
        set_up_nested_soc_bdg,
        "keys": {}
    }
)


class SiestaBdGSimpleIterator(SiestaIterator):
    _process_class = SiestaBdGSimpleWorkChain
    _params_lookup = SIESTA_BDG_ITERATION_PARAMS
