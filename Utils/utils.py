# pylint: disable=line-too-long,invalid-name,pointless-string-statement,too-many-arguments,too-many-locals
"""
Utils for main.py.
"""
import pathlib
from dataclasses import dataclass
#from typing import Callable
import pandas as pd
import toml_utils as tmut
import uniprot_utils as uput  # in my Utils/ folder
import ensembl_rest_utils as erut  # in my Utils/ folder


# configuration Toml file
Cnfg_Toml_file: pathlib.Path = pathlib.Path('./config/config.toml')

class Configuration_Error(Exception):
    """Invalid configuration exception."""
    def __init__(self, message: str):
        self.message: str = message

    def __str__(self):
        return repr(f"{self.message}. Please check {str(Cnfg_Toml_file)}.")


@dataclass
class Labels:
    """Label names."""
    Transcript_ID: str = 'Transcript_ID'
    Protein_ID: str = 'Protein_ID'
    Gene_name: str = 'Gene_name'
    Gene_ID: str = 'Gene_ID'
    UniProt_ID: str = 'UniProt_ID'
    UniProt_URL: str = 'UniProt_URL'
    Domains: str = 'Domains'

# update Uniprot_url_template based on uniprot_id
#get_uniprot_url: Callable[[str], str] = lambda uniprot_id: f"https://www.uniprot.org/uniprotkb/{uniprot_id}/entry"
def get_uniprot_url(uniprot_id: str) -> str:
    """Returns the UniProt URL of a UniProt ID."""
    return f"https://www.uniprot.org/uniprotkb/{uniprot_id}/entry"

def check_configuration(cnfg_data: dict) -> None:
    """Check configuration validity."""
    assert cnfg_data['Assembly']['version'] in ["GRCh37", "GRCh38"], f"Aeembly version {cnfg_data['Assembly']['version']} not supported !!"
    assert cnfg_data['Output']['format'] in ["basic", "compact", "expanded"], f"Output format {cnfg_data['Output']['format']} not supported !!"
    if not pathlib.Path(cnfg_data['Transcript']['file']).is_file():
        raise FileNotFoundError(f"Cannot find input transcript file {cnfg_data['Transcript']['file']} !!")
    if not isinstance(cnfg_data['Domains']['uniprot_features'], list):
        raise TypeError(f"Domain:features in {Cnfg_Toml_file} must contain a list of UniProt domains !!")
    if (pathlib.Path(cnfg_data['Output']['file']).suffix == '.csv') and (cnfg_data['Output']['format'] == 'expanded'):
        raise Configuration_Error("CSV output file not supported for 'expanded' output format !!")
    if pathlib.Path(cnfg_data['Output']['file']).suffix not in ['.xlsx', '.xls', '.csv']:
        raise Configuration_Error(f"Output file {cnfg_data['Output']['file']} not supported (only excel and CSV are supported) !!")


def load_config() -> dict:
    """Loads the Toml configuration file."""
    cnfg_data = tmut.myToml().load(Cnfg_Toml_file)
    # verify configuration validity
    check_configuration(cnfg_data)
    return cnfg_data

def print_config(cnfg_data: dict) -> None:
    """Pretty print of config data."""
    tmut.print_nested_dicts(cnfg_data)

# this function was taken from myutils.py
def dfs_to_excel_file(dfs: list[pd.DataFrame], excel_file_name: str, sheet_names: list[str],
                      add_index: bool = False,
                      na_rep: str = 'NaN',
                      float_format: str | None = None,
                      extra_width: int = 0,
                      header_format: dict | None = None) -> None:
    """
    Write DataFrames to excel (each in a separate sheet), while auto adjusting column widths based on the data.
    """
    if len(dfs) != len(sheet_names):
        raise ValueError("dfs_to_excel_file: the numbers of dfs and sheet names must match !!")

    with pd.ExcelWriter(excel_file_name) as writer:
        for sheet_name, df in zip(sheet_names, dfs):
            df.to_excel(writer, sheet_name=sheet_name, index=add_index, na_rep=na_rep, float_format=float_format)

            # Auto-adjust columns' width
            worksheet = writer.sheets[sheet_name]
            for column in df.columns:
                column_width = max(df[df[column].notna()][column].astype(str).map(len).max(), len(column)) + extra_width  # this first removes NA values from the column
                col_idx = df.columns.get_loc(column)
                worksheet.set_column(col_idx, col_idx, column_width)

            if header_format is not None:
                h_format = writer.book.add_format(header_format)
                for col_num, value in enumerate(df.columns.values):
                    worksheet.write(0, col_num, value, h_format)

# def load_transcripts(cnfg_data) -> list[str]:
#     """
#     Loading transcripts from input file.
#     [this does not cause a Pylint warning in main.py when using u.load_transcripts(cnfg_data) claiming that this is non-iterable]
#     """
#     if (file := pathlib.Path(cnfg_data['Transcript']['file'])).suffix == '.txt':
#         return load_transcripts_text(cnfg_data)
#     if file.suffix == '.csv':
#         return load_transcripts_csv(cnfg_data)
#     raise ValueError(f"Input file {file} format not supported !!")


def load_transcripts(cnfg_data: dict) -> list[str]:
    """
    Loading transcripts from input file.
    """
    match (file := pathlib.Path(cnfg_data['Transcript']['file'])).suffix:
        case ".txt":
            return load_transcripts_text(cnfg_data)
        case ".csv":
            return load_transcripts_csv(cnfg_data)
        case _:
            raise ValueError(f"Input file {file} format not supported !!")

def load_transcripts_csv(cnfg_data: dict) -> list[str]:
    """
    Loading transcript IDs from the input csv file and returning the transcript IDs.
    """
    try:
        return pd.read_csv(cnfg_data['Transcript']['file'], sep=cnfg_data['Transcript']['csv_sep'])[cnfg_data['Transcript']['csv_file_transcript_col_name']].unique().tolist()
    except (FileNotFoundError, KeyError) as e:
        print(f"Error in loading transcripts from the column {cnfg_data['Transcript']['csv_file_transcript_col_name']} in {cnfg_data['Transcript']['file']} file: {e}")
        raise

def load_transcripts_text(cnfg_data: dict) -> list[str]:
    """Loading transcript IDs from the input text file and returning the transcript IDs."""
    try:
        with open(cnfg_data['Transcript']['file'], 'rt', encoding='UTF-8') as fp:
            return [x for x in [line.rstrip() for line in fp] if 'ENST' in x]
    except FileNotFoundError:
        print(f"Can not find input transcripts file {cnfg_data['Transcript']['file']}. Please check configuration file, under ['Transcript']['file'] !!")
        raise

def get_transcripts_IDs(cnfg_data: dict, transcripts: list[str]) -> dict[str,dict[str,str]]:
    """
    Retreives different IDs of a transcript.
    """
    rapi = erut.REST_API(cnfg_data['Assembly']['version'])
    info: dict = {}
    for transcript in transcripts:
        # Gene ID and name
        if cnfg_data['IDs']['show_gene_name'] or cnfg_data['IDs']['show_gene_id']:
            ensg_id = rapi.get_transcript_parent(transcript)
            if cnfg_data['IDs']['show_gene_name'] :
                ensg_name = '' if ensg_id == '' else rapi.ENSG_id2symbol(ensg_id)

        uniprot_id = uput.ensembl_id2uniprot_id(transcript)
        info[transcript] = {
            Labels.Protein_ID: rapi.transcript_id2protein_id(transcript) if cnfg_data['IDs']['show_protein_id'] else '',
            Labels.Gene_ID: ensg_id if cnfg_data['IDs']['show_gene_id'] else '',
            Labels.Gene_name: ensg_name if cnfg_data['IDs']['show_gene_name'] else '',
            Labels.UniProt_ID: uniprot_id,
            Labels.UniProt_URL: get_uniprot_url(uniprot_id) if cnfg_data['IDs']['show_uniprot_url'] else ''
        }
    return info

def get_uniprot_domains(cnfg_data: dict, transcripts_ids: dict[str,dict[str,str]]) -> dict[str,dict]:
    """Get UniProt domains given the UniProt ID."""
    info: dict = {}
    features: list = cnfg_data['Domains']['uniprot_features']
    for transcript, transcript_ids in transcripts_ids.items():
        if (df_uniprot := uput.retrieve_protein_data_features_subset(transcript_ids[Labels.UniProt_ID], features)).empty:
            print(f"\n[** No {features} UniProt features were found for {transcript} (UniProt ID={transcript_ids[Labels.UniProt_ID]}) **]\n")
            # we do not use continue so that the domains for this transcript will be empty in the output file
        info[transcript] = {
            'domains_df': df_uniprot,  # in a dataframe format
            'domains_list': list(df_uniprot.T.to_dict().values())  # in a list of domains format
        } | transcript_ids
    return info

def _append_optional_IDs_to_df(cnfg_data: dict, df: pd.DataFrame, start_index: int, ids_dict: dict) -> pd.DataFrame:
    """Append optional ID columns based on configuration to inut dataframe."""
    dfc = df.copy()
    if cnfg_data['IDs']['show_uniprot_id']:
        dfc.insert(start_index, Labels.UniProt_ID, ids_dict[Labels.UniProt_ID])
        start_index += 1
    if cnfg_data['IDs']['show_gene_id']:
        dfc.insert(start_index, Labels.Gene_ID, ids_dict[Labels.Gene_ID])
        start_index += 1
    if cnfg_data['IDs']['show_gene_name']:
        dfc.insert(start_index, Labels.Gene_name, ids_dict[Labels.Gene_name])
        start_index += 1
    if cnfg_data['IDs']['show_protein_id']:
        dfc.insert(start_index, Labels.Protein_ID, ids_dict[Labels.Protein_ID])
        start_index += 1
    if cnfg_data['IDs']['show_uniprot_url']:
        dfc.insert(start_index, Labels.UniProt_URL, ids_dict[Labels.UniProt_URL])
    return dfc

def _gen_basic_domain_dataframe(cnfg_data: dict, transcripts_domains: dict[str,dict]) -> pd.DataFrame:
    """Generate a dataframe with all transcripts, where each domain is listed in a separate row."""
    all_dfs: list = []
    for k, v in transcripts_domains.items():
        df: pd.DataFrame = v['domains_df'].copy()
        df.insert(0, Labels.Transcript_ID, k)
        df = _append_optional_IDs_to_df(cnfg_data, df, 1, v)
        all_dfs.append(df)
    return pd.concat(all_dfs).reset_index(drop=True)

def _gen_compact_domain_dataframe(cnfg_data: dict, transcripts_domains: dict[str,dict]) -> pd.DataFrame:
    """Generate a dataframe with all transcripts, where all domains of a transcript are aggregate into a single row."""
    all_dfs: list = []
    for k, v in transcripts_domains.items():
        df = pd.DataFrame({
            Labels.Transcript_ID: k,
        }, index=[0])
        df = _append_optional_IDs_to_df(cnfg_data, df, 1, v)
        df[Labels.Domains] = "|".join([",".join([f"{k}:{v}" for k, v in x.items()]) for x in v['domains_list']])
        all_dfs.append(df)
    return pd.concat(all_dfs).reset_index(drop=True)

def generate_output_table(cnfg_data: dict, transcripts_domains: dict[str,dict]) -> tuple[list[pd.DataFrame],list[str]]:
    """Returns the output dataframe containing IDs and domains."""
    match cnfg_data['Output']['format']:
        case 'basic':
            dfs = [_gen_basic_domain_dataframe(cnfg_data, transcripts_domains)]
            transcript_IDs = [Labels.Domains]  # when all transcripts are in the same sheet, we simply call the sheet Labels.Domains]
        case 'compact':
            dfs = [_gen_compact_domain_dataframe(cnfg_data, transcripts_domains)]
            transcript_IDs = [Labels.Domains]  # when all transcripts are in the same sheet, we simply call the sheet Labels.Domains]
        case 'expanded':
            df = _gen_basic_domain_dataframe(cnfg_data, transcripts_domains)
            transcript_IDs, dfs = zip(*list(df.groupby(by=Labels.Transcript_ID)))  # sheet name is the transcript ID
            dfs = [dfx.drop(columns=[Labels.Transcript_ID]) for dfx in dfs]  # remove transcript ID columns, since it is the sheet name
        case _:
            raise ValueError(f"Output format {cnfg_data['Output']['format']} is no supported. Please check configuration file, under ['Output']['format'] !!")
    return dfs, transcript_IDs

def generate_output_file(cnfg_data: dict, transcripts_domains: dict[str,dict]) -> None:
    """Generates the ouput file containing the IDs and domains"""
    dfs, sheet_names = generate_output_table(cnfg_data, transcripts_domains)
    match pathlib.Path(cnfg_data['Output']['file']).suffix:
        case '.csv':
            dfs[0].to_csv(cnfg_data['Output']['file'], sep=',', index=False)
        case '.xlsx' | '.xls':
            dfs_to_excel_file(dfs, cnfg_data['Output']['file'], sheet_names=sheet_names, add_index=False, extra_width=2)
        case _:
            raise Configuration_Error(f"Output file {cnfg_data['Output']['file']} not supported (only excel and CSV are supported) !!")
