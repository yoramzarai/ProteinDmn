""" 
Activate environment and run "pytest".
"""
from pathlib import Path

import Utils.utils as u


def test_config_is_valid() -> None:
    # load configuration
    cnfg_data = u.load_config()

    # check Transcripts file
    tr = Path(cnfg_data['Transcript']['file'])
    assert tr.is_file(), f"Transcript file {tr} does not exist."
    assert tr.suffix in ['.txt', '.csv', '.CSV', '.TXT'], \
        f"Transcript file {tr} suffix must be .txt or .csv !!"
    
    if tr.suffix in ['.csv', '.CSV']:
        assert cnfg_data['Transcript']['csv_file_transcript_col_name'] != '', \
        "In case of an input CSV file, csv_file_transcript_col_name must be set !!"

        assert cnfg_data['Transcript']['sep'] != '' \
        "In case of an input CSV file, sep must be set !!"
    
    # check assembly version
    assert cnfg_data['Assembly']['version'] in ['GRCh38', 'GRCh37'], \
        f"Assembly version {cnfg_data['Assembly']['version']} not supported !!"
    
    # check output version
    assert cnfg_data['Output']['format'] in ['basic', 'compact', 'expanded'], \
        f"Output format {cnfg_data['Ouput']['format']} not supported !!"

    # bool types
    bool_types: list[bool] = [
        cnfg_data['Debug']['enable'],
        cnfg_data['IDs']['show_gene_id'],
        cnfg_data['IDs']['show_gene_name'],
        cnfg_data['IDs']['show_protein_id'],
        cnfg_data['IDs']['show_uniprot_id'],
        cnfg_data['IDs']['show_uniprot_url']
    ]
    assert all(isinstance(x, bool) for x in bool_types), \
        "All boolean values must be of type bool !!"