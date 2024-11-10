# pylint: disable=line-too-long,invalid-name,pointless-string-statement,too-many-arguments
"""
Utils for UniProt (https://www.uniprot.org) REST API.
"""
from functools import partial
from typing import Callable
import pandas as pd

import rest_api_utils as rsut


Uniprot_base_URL: str = "https://rest.uniprot.org/uniprotkb"
Uniprot_stream_URL: str = f"{Uniprot_base_URL}/stream"

endpoint_get_base = partial(rsut.endpoint_get_base, server=Uniprot_base_URL)
#endpoint_post_base = partial(rsut.endpoint_post_base, server=Uniprot_base_URL)

endpoint_get_stream = partial(rsut.endpoint_get_base, server=Uniprot_stream_URL)
#endpoint_post_stream = partial(rsut.endpoint_post_base, server=Uniprot_URL)


def uniprot_id2ensembl_id(uniprot_id: str) -> str:
    """Retrieves the Ensembl ENST ID corresponding to a uniprot ID."""
    if (df := get_CrossReferences_databases_info(uniprot_id)).empty:
        print(f"No cross-reference information available for {uniprot_id=} !!")
        return ''
    try:
        return df.query("database == 'Ensembl'").iloc[0]['id']
    except IndexError:
        print(f"No Ensembl information available for {uniprot_id=}!!")
        return ''


def ensembl_id2uniprot_id(ensb_id: str) -> str:
    """Retrieves the UniProt ID based on an Ensembl transcript or protein ID."""
    return lookup_protein_data_ensb_based_entry(ensb_id, 'primaryAccession')


# this should be eventially removed (here for backward compatability)
lookup_accession: Callable[[str], str] = ensembl_id2uniprot_id


def lookup_protein_data(uniprot_id: str) -> dict:
    """Retrieves all protein data from UniProt."""
    return rsut.endpoint_get_base(server=f"{Uniprot_base_URL}/{uniprot_id}", params={'format': 'json'})


def retrieve_protein_data_field(uniprot_id: str, field: str) -> dict | str:
    """
    Returns protein field information.
    For example, field='features' returns all features.
    """
    try:
        return lookup_protein_data(uniprot_id)[field]
    except (KeyError, TypeError):
        return {}


def retrieve_protein_data_features_subset(uniprot_id: str, subset_featuer_types: list) -> pd.DataFrame:
    """
    Retrieve a subset of the protein features.

    Use this to retrieve protein domains by setting
    subset_featuer_types to ["Topological domain", "Transmembrane", "Domain"].
    """
    try:
        fc = [
            pd.Series(
                {
                    'type': feature['type'],
                    'start': feature['location']['start']['value'],
                    'end': feature['location']['end']['value'],
                    'description': feature['description']
                }
            )
            for feature in retrieve_protein_data_field(uniprot_id, "features")
        ]
    except (KeyError, TypeError) as e:
        print(f"Error in retrieve_protein_data_features_subset: {e}")
        return pd.DataFrame()
    if not fc:
        return pd.DataFrame()

    df = pd.DataFrame(fc)
    return df.query(f"type in {subset_featuer_types}").reset_index(drop=True) if subset_featuer_types else df


def AA_seq(uniprot_id: str) -> str:
    """Returns the AA sequence."""
    try:
        return lookup_protein_data(uniprot_id)['sequence']['value']
    except (KeyError, TypeError) as e:
        print(f"Error in AA_seq: {e}")
        return ''


def get_CrossReferences_databases_info(uniprot_id: str) -> pd.DataFrame:
    """Gather all uniProtKBCrossReferences field databases information into a dataframe."""
    try:
        info = lookup_protein_data(uniprot_id)
    except (KeyError, TypeError) as e:
        print(f"Error in get_CrossReferences_databases_info: {e}")
        return pd.DataFrame()

    fs = [
        pd.Series(
            {
                'database': itm['database'],
                'id': itm['id'],
                'properties': itm['properties']

            }
        )
        for itm in info['uniProtKBCrossReferences']
        if 'database' in itm
        ]
    return pd.DataFrame(fs)


"""
The following functions are based on Ensembl ENST or ENSP ID.
=============================================================
"""
def lookup_protein_data_ensb_based(ensb_id: str) -> dict:
    """pid is either a transcript ID (ENST), a protein ID (ENSP), or a UniProt ID."""
    d = endpoint_get_stream(params={'format': 'json', 'query': ensb_id})
    return {} if not d['results'] else d


def lookup_protein_data_ensb_based_entry(ensb_id: str, entry_name: str) -> str:
    """Gets an entry from the protein query structure."""
    d = lookup_protein_data_ensb_based(ensb_id)
    try:
        return d['results'][0][entry_name]
    except KeyError as e:
        print(f"Error in lookup_protein_data_ensb_based_entry for {ensb_id=}: {e}")
        return ''


def retrieve_features_ensb_based(ensb_id: str) -> pd.DataFrame:
    """Retrieves protain features."""
    try:
        info = lookup_protein_data_ensb_based(ensb_id)['results'][0]
    except (KeyError, TypeError) as e:
        print(f"Error in retrieve_features_ensb_based for {ensb_id=}: {e}")
        return pd.DataFrame()

    # gather features into a dataframe
    fs = [
        pd.Series(
            {
                'type': feature['type'],
                'start': feature['location']['start']['value'],
                'end': feature['location']['end']['value'],
                'description': feature['description'],
                }
                )
        for feature in info['features']
    ]
    return pd.DataFrame(fs)


def retrieve_sub_features_ensb_based(ensb_id: str, sub_features: list) -> pd.DataFrame:
    """Retrieves a subset of features based on a list of features."""
    if (df := retrieve_features_ensb_based(ensb_id)).empty:
        return pd.DataFrame()
    return df.query(f"type in {sub_features}").reset_index(drop=True) if sub_features else df


def AA_seq_ensb_based(ensb_id: str) -> str:
    """Returns the AA sequence."""
    try:
        return lookup_protein_data_ensb_based(ensb_id)['results'][0]['sequence']['value']
    except (KeyError, TypeError) as e:
        print(f"Error in AA_seq for {ensb_id=}: {e}")
        return ''
