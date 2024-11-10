# Retrieve Protein Domains

Retrieving protein domains from [UniProt](https://www.uniprot.org) based on Ensembl transcript ID.

Given a list of Ensembl transcript IDs (i.e. `ENST` IDs), we:
1. Retrieve the corresponding protein ID, gene name and ID, UniProt ID, and UniProt URL.
1. Retrieve the protein domains from UniProt.
1. Generate an excel file containing the IDs and protein domains.


# Configuration File
`./config/config.toml`

# Input
A text file or a CSV file containing the Ensembl transcript IDs (file name defined in `./config/config.toml`). In case of a text file, each transcript ID is listed in a separate line. In case of a CSV file, the column name holding the transcript IDs, and the CSV delimiter, are defined in `./config/config.toml`.

An example of an input text file:
```python 
ENST00000288135
ENST00000302278
ENST00000559488
```

# Output
An excel or CSV file containing the corresponding protein domains (file name defined in `./config/config.toml`).

# Execution Flow
1. Set the configuration parameters in `./config/config.toml`
1. Run `./main.py`

# Requirements
1. Python >= 3.11
1. pandas
1. XlsxWriter
1. requests
1. toml

# Additional Stand Alone Features
Converting Ensembl ID to UniProt ID.

```python
# Example
import Utils.uniprot_utils as uput
uniprot_id: str = uput.ensembl_id2uniprot_id('ENST00000559488')
```

Converting UniProt ID to Ensembl ID.

```python
# Example
import Utils.uniprot_utils as uput
ensembl_id: str = uput.uniprot_id2ensembl_id('P05106')
```

Retrieving the AA sequence.

```python
# Example
import Utils.uniprot_utils as uput
aa_seq: str = uput.AA_seq('P05106')
```

Retrieving cross-reference information.

```python
# Example
import Utils.uniprot_utils as uput
df_cross_reference: pd.DataFrame = uput.get_CrossReferences_databases_info('P05106')
```

Retrieving all protein data.

```python
# Example
import Utils.uniprot_utils as uput
protein_data: dict = uput.lookup_protein_data('P05106')
```

