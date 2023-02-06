"""Script to generate the parameters files for the different measures.
"""

import json

measure_params = {
    'R': {
        'use': {
            'vm1': {'threshold': 50},
            'vm2': {'threshold0': 10, 'threshold1': 50},
            'vm1_wf': {},
            'vm2_wf': {},
        },
        'int': {
            'vm1': {},
            'vm2': {},
            'vm1_wf': {},
            'vm2_wf': {},
        }
    },
    'L': {
        'use': {
            'vm1': {'threshold': 50},
            'vm2': {'threshold0': 10, 'threshold1': 50},
            'vm1_wf': {},
            'vm2_wf': {},
        },
        'int': {
            'vm1': {},
            'vm2': {},
            'vm1_wf': {},
            'vm2_wf': {},
            
        }
    },
    'W': {
        'use': {
            'vm1': {'threshold': 1},
            'vm2': {'threshold0': 1, 'threshold1': 2},
            'vm1_wf': {},
            'vm2_wf': {},
        },
        'int': {
            'vm1': {},
            'vm2': {},
            'vm1_wf': {},
            'vm2_wf': {},
            
        }
    },
}

with open("../dashdata/measures_params.json", "w") as fh:
    json.dump(measure_params, fh, indent=4)
