# pylint: disable=line-too-long,invalid-name,pointless-string-statement,too-many-arguments,too-many-lines
# type: ignore  # for Pylance
"""
Utils for the Ensembl REST API (https://rest.ensembl.org)

Examples:
    a = lookup_id("ENST00000532448") # or
    a = lookup_id("ENSG00000172818") # or
    a = lookup_symbol("BRCA2")

    # display information
    for i, (k, v) in enumerate(a.items(), start=1):
        print(f"{i}. {k}: {v}")

See also /Explore_ensembl_REST/example_ensembl_rest.ipynb for few usage examples.

For APIs that are not implemented here, use the function endpoint_get_base
or endpoint_post_base and set the 'ext' parameter (and maybe also 'params', 'headers', and 'data' parameters) accordingly.
For example (see https://rest.ensembl.org/documentation/info/ontology_name):
         endpoint_get_base(ext="/ontology/name/transcription factor complex?", headers={ "Content-Type" : "application/json"})

Updated on 12/20/23 - using rest_api_utils.py
"""

from functools import partial, partialmethod
from requests.exceptions import HTTPError

import Utils.rest_api_utils as rsut

# supported assemblies
Ensembl_URLs: dict[str, str] = {
    'GRCh38': "https://rest.ensembl.org",
    'GRCh37': "https://grch37.rest.ensembl.org"
}

# Converts Ensembl sequence type names.
# See, e.g., the type parameter in https://rest.ensembl.org/documentation/info/sequence_id
Ensb_seq_types: dict[str, str] = {
    'genomic': 'pre-RNA',  # a sequence containing Exon1, Intron1, Exon2, Intron2, ..., Exonm
    'cdna': 'RNA',  # a sequence containing Exon1, Exon2, ..., Exonm
    'cds': 'ORF',
    'protein': 'AA'
    }


Ensb_gene_ID_preamble: str = 'ENSG'
Ensb_transcript_ID_preamble: str = 'ENST'
Ensb_exon_ID_preamble: str = 'ENSE'


class REST_API():
    """REST API class."""
    def __init__(self, assembly: str = 'GRCh38'):
        try:
            self.URL = Ensembl_URLs[assembly]
        except KeyError:
            print(f"{assembly=} is not supported (only {','.join(list(Ensembl_URLs.keys()))} are supported) !!")
            raise
        self.endpoint_get_base = partial(rsut.endpoint_get_base, server=self.URL)
        self.endpoint_post_base = partial(rsut.endpoint_post_base, server=self.URL)

    """
    Lookup endpoint
    ===============
    """
    def lookup_endpoint_base(self, ID: str, typ: str, headers: dict, options: str = 'expand=1;utr=1') -> dict | str:
        """
        Base lookup command.
        options - a ';' separated option=value string. See https://rest.ensembl.org/documentation/info/lookup.
        """
        return self.endpoint_get_base(ext=f"/lookup/{typ}/{ID}?{options}", headers=headers)


    """look_id(ID). Information about a given ID. For example, look_id('ENSG00000172818')"""
    lookup_id = partialmethod(lookup_endpoint_base, typ='id', headers={"Content-Type": "application/json"})

    def lookup_symbol(self, symbol: str, species: str = 'homo_sapiens', options: str = 'expand=1') -> dict:
        """Information about a gene symbol (e.g. MET) of a species."""
        return self.lookup_endpoint_base(f"{species}/{symbol}", 'symbol', {"Content-Type": "application/json"}, options=options)


    def get_canonical_transcript(self, gene: str) -> str:
        """Given a gene, returns it 'canonical' transcript by Ensembl. 'gene' can be an ENSG ID or a symbol (e.g., MET)."""
        return self.lookup_id(gene)['canonical_transcript'] if Ensb_gene_ID_preamble in gene else self.lookup_symbol(gene)['canonical_transcript']


    def get_transcripts_of_gene(self, gene: str) -> dict:
        """
        Given a gene (defined by either its ENSG ID or its symbol name (e.g. MET)), the function returns
        a dictionary with keys that are transcript IDs and values that are the biotype.
        """
        info = self.lookup_id(gene) if Ensb_gene_ID_preamble in gene else self.lookup_symbol(gene)
        return {x['id']: x['biotype'] for x in info['Transcript']}


    def get_transcript_start_end(self, trans_id: str) -> tuple[int, int]:
        """
        Given a transcript ID (ENST), the function returns a tuple containing (TSS, TES), i.e.
        the (primary) transcript start and end site coordinates, respectively.
        TSS [TES] is the coordinate of the first [last] bp of the first [last] exon.
        
        Note that TSS > TES for transcripts encoded on the negative strand, otherwise TSS < TES.
        """
        if Ensb_transcript_ID_preamble not in trans_id:
            print(f"get_transcripts_sizes: input ID must be a transcript ID (i.e. a {Ensb_transcript_ID_preamble} ID) and not {trans_id} !!")
            return -1, -1
        info = self.lookup_id(trans_id)
        return (info['start'], info['end']) if info['strand'] == 1 else (info['end'], info['start'])


    def get_transcript_sizes(self, trans_id: str) -> tuple[int, int]:
        """
        Given a transcript ID (ENST), the function returns a tuple containing the transcript (RNA)
        size in bps and the protein size in AAs.

        If the transcript is not a protein-coding transcript, the AA size returned is set to -1. 
        """
        if Ensb_transcript_ID_preamble not in trans_id:
            print(f"get_transcripts_sizes: input ID must be a transcript ID (i.e. a {Ensb_transcript_ID_preamble} ID) and not {trans_id} !!")
            return -1, -1
        info = self.lookup_id(trans_id)
        aa_len = info['Translation']['length'] if 'Translation' in info else -1
        return info['length'], aa_len


    def get_transcripts_sizes_of_gene(self, gene: str) -> dict:
        """
        Given a gene (defined by either its ENSG ID or its symbol name (e.g. MET)), the function returns
        a dictionary with keys that are transcript IDs and values that are a tuple containing the transcript (RNA)
        size in bps and protein size in AAs.

        If the transcript is not a protein-coding transcript, the AA size returned is set to -1. 
        """
        info = self.lookup_id(gene) if Ensb_gene_ID_preamble in gene else self.lookup_symbol(gene)
        return {x['id']: self.get_transcript_sizes(x['id']) for x in info['Transcript']}


    def get_gene_strand(self, gene: str) -> int:
        """
        Given a gene (defined by either its ENSG ID or its symbol name (e.g. MET)), the function returns
        1 [-1] if the gene is encoded on the forward [reveresed] DNA strand.
        """
        return int(self.lookup_id(gene)['strand']) if Ensb_gene_ID_preamble in gene else int(self.lookup_symbol(gene)['strand'])


    def get_transcript_version(self, trans_id: str) -> str:
        """Returns the transcript version of a transcript ID."""
        return self.lookup_id(trans_id)['version']


    def get_transcript_parent(self, trans_id: str) -> str:
        """Returns the gene ID containing the transcript trans_id."""
        info = self.lookup_id(trans_id)
        try:
            return info['Parent'] if isinstance(info, dict) else ''
        except KeyError:
            return ''


    """
    Info data
    =========
    """
    def get_release_info(self, content_type: str = 'application/json') -> dict | str:
        """Shows the data releases available on the REST server."""
        return self.endpoint_get_base(ext="/info/data/?", headers={"Content-Type" : content_type})


    def get_assembly_info(self, ext: str = "/info/assembly/homo_sapiens?", content_type: str = 'application/json', params: dict = None) -> dict | str:
        """Get assembly information."""
        return self.endpoint_get_base(ext=ext, headers={"Content-Type" : content_type}, params=params)


    def get_assembly_chromosome_info(self, chrm_num: str, ext: str = "/info/assembly/homo_sapiens", content_type: str = 'application/json', params: dict = None) -> dict | str:
        """Get assembly information of a given chromosome. chrm_num is a single character (e.g., '1', or 'X')."""
        return self.endpoint_get_base(ext=f"{ext}/{chrm_num.upper()}", headers={"Content-Type" : content_type}, params=params)


    def get_consequence_types(self, ext: str = "/info/variation/consequence_types?", content_type: str = 'application/json') -> dict | str:
        """Information on all consequence types."""
        return self.endpoint_get_base(ext=ext, headers={"Content-Type" : content_type})


    def is_protein_coding(self, trans_id: str) -> bool:
        """Returns True [False] if the transcript ID trans_id is [is not] a coding protein transcript."""
        if Ensb_transcript_ID_preamble not in trans_id:
            print(f"Input ({trans_id}) must be a valid transcript ID (i.e. a {Ensb_transcript_ID_preamble} ID) !!")
            return False
        return self.lookup_id(trans_id)['biotype'] == 'protein_coding'


    """
    Sequence endpoint
    =================
    """
    def get_UTRs(self, trans_id: str) -> tuple[str, str]:
        """Return a tuple containing the 5'UTR (first item) followed by the 3'UTR (second item) sequences of a transcript."""
        try:
            mrna = self.sequence_endpoint_base(trans_id, seq_type='cdna')
            cds = self.sequence_endpoint_base(trans_id, seq_type='cds')
        except HTTPError:
            print(f"Can not retrieve mRNA and/or CDS of the transcript {trans_id}. Make sure this is a protein-coding transcript !!")
            raise
        else:
            if (index := mrna.find(cds)) == -1:  # index is 0-based
                print(f"Can not find the CDS sequence in the mRNA sequence for {trans_id} .......")
                return '', ''
            return mrna[:index], mrna[index+len(cds):]


    def sequence_endpoint_base(self, ID: str, seq_type: str = None, content_type: str =  "text/plain") -> dict | str:
        """
        Get a sequence of an ID.
        
        If ID is a transcript ID (e.g. ENST) use:
        1. seq_type='genomic' to get the primary transcript (pre-mRNA) sequence,
        2. seq_type='cdna' to get the spliced transcript sequence with UTR (i.e. RNA),
        3. seq_type='cds' to get the spliced transcript sequence without UTR (i.e. ORF),
        4. seq_type='5UTR' to get the 5'UTR sequence,
        5. seq_type='3UTR' to get the 3'UTR sequence,
        6. seq_type='protein' to get the protein sequence.
        """
        if 'UTR' in seq_type:
            if Ensb_transcript_ID_preamble in ID:
                utrs = self.get_UTRs(ID)
                return utrs[0] if seq_type == '5UTR' else utrs[1]
            print(f"{seq_type=} allowed only for transcript ID ({Ensb_transcript_ID_preamble}), but input ID is {ID} !!")
            return ''
        else:
            ext = f"/sequence/id/{ID}?" if seq_type is None else f"/sequence/id/{ID}?type={seq_type}"
            return self.endpoint_get_base(ext=ext, headers={"Content-Type": content_type})


    def sequence_region_endpoint_base(self, chromosome_num: str, start_pos: int, end_pos: int, strand: int = 1,
                                      species: str = 'homo_sapiens', content_type: str =  "text/plain") -> dict | str:
        """
        Retrieves a DNA sequence from start_pos to end_pos in chromosome chromosome_num.
        If strand==-1, returns the reversed-complement of the forward strand sequence, otherwise (strand==1) returns
        the forward strand sequence.
        Positions are 1-based.
        Example for chromosome_num: '1', or 'X'.
        """
        return self.endpoint_get_base(ext=f"/sequence/region/{species}/{chromosome_num.upper()}:{start_pos}..{end_pos}:{strand}?",
                                      headers={"Content-Type": content_type})


    """
    Conversions
    ===========
    """
    def cdna2genomic(self, trans_id: str, start: int, end: int, ext: str = "/map/cdna", content_type: str = 'application/json') -> dict | str:
        """
        cDNA (i.e. RNA) to genomic coordinate conversion. For example, start=end=1 returns the chromosome coordinate of the first
        bp in the RNA.
        """
        return self.endpoint_get_base(ext=f"{ext}/{trans_id}/{start}..{end}?", headers={"Content-Type" : content_type})


    def CDS2genomic(self, trans_id: str, start: int, end: int, ext: str = "/map/cds", content_type: str = 'application/json') -> dict | str:
        """
        CDS (i.e. ORF) to genomic coordinate conversion.
        For example, start=end=1 returns the chromosome coordinate of the first
        bp in the ORF.
        """
        return self.endpoint_get_base(ext=f"{ext}/{trans_id}/{start}..{end}?", headers={"Content-Type" : content_type})


    def protein2genomic(self, protein_id: str, start: int, end: int, ext: str = "/map/translation", content_type: str = 'application/json') -> dict | str:
        """
        Protein (AA sequence) to genomic coordinate conversion. For example, start=end=1 returns the chromosome coordinate of the first
        AA in the protein.
        """
        return self.endpoint_get_base(ext=f"{ext}/{protein_id}/{start}..{end}?", headers={"Content-Type" : content_type})


    def assembly_coordinate_conversions(self,
                                        start: int, end: int, chrm: str, ext: str = "/map/human",
                                        input_assembly: str = 'GRCh37', output_assembly: str = 'GRCh38', strand: int = 1,
                                        content_type: str = 'application/json') -> dict | str:
        """Converts coordinates from input assembly to output assembly."""
        return self.endpoint_get_base(ext=f"{ext}/{input_assembly}/{chrm}:{start}..{end}:{strand}/{output_assembly}?", headers={"Content-Type" : content_type})


    def symbol2ENSG_id(self, symbol: str, species: str = 'homo_sapiens') -> str:
        """Converts a symbol (e.g. PIK3CA) to ID (e.g. ENSG00000121879)."""
        try:
            return self.lookup_symbol(symbol, species=species)['id']
        except KeyError:
            return ''


    def ENSG_id2symbol(self, eid: str) -> str:
        """Converts ID (e.g. ENSG00000121879) to symbol (e.g. PIK3CA)."""
        try:
            return self.lookup_id(eid)['display_name']
        except KeyError:
            return ''


    #def transcript_id2protein_id(self, trans_id: str) -> str:
    #    """Retrieves the protein ID (ENSP) of a given transcript ID (ENST)."""
    #    return self.lookup_id(trans_id)['Translation']['id']


    def transcript_id2protein_id_with_version(self, trans_id: str) -> str:
        """Retrieves the protein ID (ENSP) with version of a given transcript ID (ENST)."""
        d = self.lookup_id(trans_id)['Translation']
        return f"{d['id']}.{d['version']}"


    def transcript_id2protein_id(self, trans_id: str) -> str:
        """Retrieves the protein ID (ENSP) of a given transcript ID (ENST)."""
        return self.transcript_id2protein_id_with_version(trans_id).split('.')[0]


    """
    Overlap Information
    ===================
    """
    def region_overlap_info(self, chrm: str, start: int, end: int, species: str = 'human', features: list = None, content_type: str = 'application/json') -> dict | str:
        """Retrieves feature information that overlaps with a chromosome region."""
        if not features:
            features = ['gene', 'transcript', 'cds']

        feature_str = ';'.join([f"feature={x}" for x in features])
        return self.endpoint_get_base(ext=f"/overlap/region/{species}/{chrm}:{start}-{end}?{feature_str}", headers={"Content-Type" : content_type})


    def protein_overlap_info(self, protein_id: str, feature_type: str = None, feature: str = 'protein_feature', content_type: str = 'application/json') -> dict | str:
        """
        Retrieves feature information that overlaps with a protein.
        Use type="Smart" to get the protein domains. Use type=None (or omit type when calling the function) to get all the features.
        """
        ext = f"/overlap/translation/{protein_id}?type={feature_type};feature={feature}" if type is not None else f"/overlap/translation/{protein_id}?feature={feature}"
        return self.endpoint_get_base(ext=ext, headers={"Content-Type" : content_type})

    """
    Variation endpoint
    ==================
    """
    def variation_endpoint_base(self, dbSNP: str, species: str = 'human', content_type: str = 'application/json') -> dict | str:
        """Retrieves the chromosome alleles and position of a given dbSNP rs value (e.g., 'rs77924615va')."""
        return self.endpoint_get_base(ext=f"/variation/{species}/{dbSNP}?",
                                headers={"Content-Type": content_type})


    def variation_variant_consequence(self, chrm: str, start: int, end: int, var_allele: str, strand: int = 1,
                                    species: str = 'human', content_type: str = 'application/json') -> dict | str:
        """
        Retrieves the consequence of a given variant.

        For INS, set end = start-1.
        For DEL, set var_allele to '-'.
        """
        return self.endpoint_get_base(ext=f"/vep/{species}/region/{chrm}:{start}-{end}:{strand}/{var_allele}?",
                                headers={"Content-Type": content_type})


# ==============================================================================================================================

# ===============================================
# OLD functional implementation
# ===============================================

# Ensembl_URL: str = "https://rest.ensembl.org"

# endpoint_get_base = partial(rsut.endpoint_get_base, server=Ensembl_URL)
# endpoint_post_base = partial(rsut.endpoint_post_base, server=Ensembl_URL)

# """
# Info data
# =========
# """
# def get_release_info(content_type: str = 'application/json') -> dict | str:
#     """Shows the data releases available on the REST server."""
#     return endpoint_get_base(ext="/info/data/?", headers={"Content-Type" : content_type})


# def get_assembly_info(ext: str = "/info/assembly/homo_sapiens?", content_type: str = 'application/json', params: dict = None) -> dict | str:
#     """Get assembly information."""
#     return endpoint_get_base(ext=ext, headers={"Content-Type" : content_type}, params=params)


# def get_assembly_chromosome_info(chrm_num: str, ext: str = "/info/assembly/homo_sapiens", content_type: str = 'application/json', params: dict = None) -> dict | str:
#     """Get assembly information of a given chromosome. chrm_num is a single character (e.g., '1', or 'X')."""
#     return endpoint_get_base(ext=f"{ext}/{chrm_num.upper()}", headers={"Content-Type" : content_type}, params=params)


# def get_consequence_types(ext: str = "/info/variation/consequence_types?", content_type: str = 'application/json') -> dict | str:
#     """Information on all consequence types."""
#     return endpoint_get_base(ext=ext, headers={"Content-Type" : content_type})


# def is_protein_coding(trans_id: str) -> bool:
#     """Returns True [False] if the transcript ID trans_id is [is not] a coding protein transcript."""
#     if not Ensb_transcript_ID_preamble in trans_id:
#         print(f"Input ({trans_id}) must be a valid transcript ID (i.e. a {Ensb_transcript_ID_preamble} ID) !!")
#         return False
#     return lookup_id(trans_id)['biotype'] == 'protein_coding'

# def get_transcript_parent(trans_id: str) -> str:
#     """Returns the gene ID containing the transcript trans_id."""
#     info = lookup_id(trans_id)
#     try:
#         return info['Parent'] if isinstance(info, dict) else ''
#     except KeyError:
#         return ''

# """
# Lookup endpoint
# ===============
# """
# def lookup_endpoint_base(ID: str, typ: str, headers: dict, options: str = 'expand=1;utr=1') -> dict | str:
#     """
#     Base lookup command.
#     options - a ';' separated option=value string. See https://rest.ensembl.org/documentation/info/lookup.
#     """
#     return endpoint_get_base(ext=f"/lookup/{typ}/{ID}?{options}", headers=headers)


# """look_id(ID). Information about a given ID. For example, look_id('ENSG00000172818')"""
# lookup_id = partial(lookup_endpoint_base, typ='id', headers={"Content-Type": "application/json"})


# def lookup_symbol(symbol: str, species: str = 'homo_sapiens', options: str = 'expand=1') -> dict:
#     """Information about a gene symbol (e.g. MET) of a species."""
#     return lookup_endpoint_base(f"{species}/{symbol}", 'symbol', {"Content-Type": "application/json"}, options=options)


# def get_canonical_transcript(gene: str) -> str:
#     """Given a gene, returns it 'canonical' transcript by Ensembl. 'gene' can be an ENSG ID or a symbol (e.g., MET)."""
#     return lookup_id(gene)['canonical_transcript'] if Ensb_gene_ID_preamble in gene else lookup_symbol(gene)['canonical_transcript']


# def get_transcripts_of_gene(gene: str) -> dict:
#     """
#     Given a gene (defined by either its ENSG ID or its symbol name (e.g. MET)), the function returns
#     a dictionary with keys that are transcript IDs and values that are the biotype.
#     """
#     info = lookup_id(gene) if Ensb_gene_ID_preamble in gene else lookup_symbol(gene)
#     return {x['id']: x['biotype'] for x in info['Transcript']}


# def get_transcript_start_end(trans_id: str) -> tuple[int, int]:
#     """
#     Given a transcript ID (ENST), the function returns a tuple containing (TSS, TES), i.e.
#     the (primary) transcript start and end site coordinates, respectively.
#     TSS [TES] is the coordinate of the first [last] bp of the first [last] exon.
    
#     Note that TSS > TES for transcripts encoded on the negative strand, otherwise TSS < TES.
#     """
#     if Ensb_transcript_ID_preamble not in trans_id:
#         print(f"get_transcripts_sizes: input ID must be a transcript ID (i.e. a {Ensb_transcript_ID_preamble} ID) and not {trans_id} !!")
#         return -1, -1
#     info = lookup_id(trans_id)
#     return (info['start'], info['end']) if info['strand'] == 1 else (info['end'], info['start'])


# def get_transcript_sizes(trans_id: str) -> tuple[int, int]:
#     """
#     Given a transcript ID (ENST), the function returns a tuple containing the transcript (RNA)
#     size in bps and the protein size in AAs.

#     If the transcript is not a protein-coding transcript, the AA size returned is set to -1. 
#     """
#     if Ensb_transcript_ID_preamble not in trans_id:
#         print(f"get_transcripts_sizes: input ID must be a transcript ID (i.e. a {Ensb_transcript_ID_preamble} ID) and not {trans_id} !!")
#         return -1, -1
#     info = lookup_id(trans_id)
#     aa_len = info['Translation']['length'] if 'Translation' in info else -1
#     return info['length'], aa_len


# def get_transcripts_sizes_of_gene(gene: str) -> dict:
#     """
#     Given a gene (defined by either its ENSG ID or its symbol name (e.g. MET)), the function returns
#     a dictionary with keys that are transcript IDs and values that are a tuple containing the transcript (RNA)
#     size in bps and protein size in AAs.

#     If the transcript is not a protein-coding transcript, the AA size returned is set to -1. 
#     """
#     info = lookup_id(gene) if Ensb_gene_ID_preamble in gene else lookup_symbol(gene)
#     return {x['id']: get_transcript_sizes(x['id']) for x in info['Transcript']}


# def get_gene_strand(gene: str) -> int:
#     """
#     Given a gene (defined by either its ENSG ID or its symbol name (e.g. MET)), the function returns
#     1 [-1] if the gene is encoded on the forward [reveresed] DNA strand.
#     """
#     return int(lookup_id(gene)['strand']) if Ensb_gene_ID_preamble in gene else int(lookup_symbol(gene)['strand'])


# def get_transcript_version(trans_id: str) -> str:
#     """Returns the transcript version of a transcript ID."""
#     return lookup_id(trans_id)['version']


# """
# Sequence endpoint
# =================
# """
# def get_UTRs(trans_id: str) -> tuple[str, str]:
#     """Return a tuple containing the 5'UTR (first item) followed by the 3'UTR (second item) sequences of a transcript."""
#     try:
#         mrna = sequence_endpoint_base(trans_id, seq_type='cdna')
#         cds = sequence_endpoint_base(trans_id, seq_type='cds')
#     except HTTPError:
#         print(f"Can not retrieve mRNA and/or CDS of the transcript {trans_id}. Make sure this is a protein-coding transcript !!")
#         raise
#     else:
#         if (index := mrna.find(cds)) == -1:  # index is 0-based
#             print(f"Can not find the CDS sequence in the mRNA sequence for {trans_id} .......")
#             return '', ''
#         return mrna[:index], mrna[index+len(cds):]


# def sequence_endpoint_base(ID: str, seq_type: str = None, content_type: str =  "text/plain") -> dict | str:
#     """
#     Get a sequence of an ID.
    
#     If ID is a transcript ID (e.g. ENST) use:
#     1. seq_type='genomic' to get the primary transcript (pre-mRNA) sequence,
#     2. seq_type='cdna' to get the spliced transcript sequence with UTR (i.e. RNA),
#     3. seq_type='cds' to get the spliced transcript sequence without UTR (i.e. ORF),
#     4. seq_type='5UTR' to get the 5'UTR sequence,
#     5. seq_type='3UTR' to get the 3'UTR sequence,
#     6. seq_type='protein' to get the protein sequence.
#     """
#     if 'UTR' in seq_type:
#         if Ensb_transcript_ID_preamble in ID:
#             utrs = get_UTRs(ID)
#             return utrs[0] if seq_type == '5UTR' else utrs[1]
#         else:
#             print(f"{seq_type=} allowed only for transcript ID ({Ensb_transcript_ID_preamble}), but input ID is {ID} !!")
#             return ''
#     else:
#         ext = f"/sequence/id/{ID}?" if seq_type is None else f"/sequence/id/{ID}?type={seq_type}"
#         return endpoint_get_base(ext=ext, headers={"Content-Type": content_type})


# def sequence_region_endpoint_base(chromosome_num: str, start_pos: int, end_pos: int, strand: int = 1,
#                                   species: str = 'homo_sapiens', content_type: str =  "text/plain") -> dict | str:
#     """
#     Retrieves a DNA sequence from start_pos to end_pos in chromosome chromosome_num.
#     If strand==-1, returns the reversed-complement of the forward strand sequence, otherwise (strand==1) returns
#     the forward strand sequence.
#     Positions are 1-based.
#     Example for chromosome_num: '1', or 'X'.
#     """
#     return endpoint_get_base(ext=f"/sequence/region/{species}/{chromosome_num.upper()}:{start_pos}..{end_pos}:{strand}?",
#                              headers={"Content-Type": content_type})

# """
# Conversions
# ===========
# """
# def cdna2genomic(trans_id: str, start: int, end: int, ext: str = "/map/cdna", content_type: str = 'application/json') -> dict | str:
#     """
#     cDNA (i.e. RNA) to genomic coordinate conversion. For example, start=end=1 returns the chromosome coordinate of the first
#     bp in the RNA.
#     """
#     return endpoint_get_base(ext=f"{ext}/{trans_id}/{start}..{end}?", headers={"Content-Type" : content_type})


# def CDS2genomic(trans_id: str, start: int, end: int, ext: str = "/map/cds", content_type: str = 'application/json') -> dict | str:
#     """
#     CDS (i.e. ORF) to genomic coordinate conversion.
#     For example, start=end=1 returns the chromosome coordinate of the first
#     bp in the ORF.
#     """
#     return endpoint_get_base(ext=f"{ext}/{trans_id}/{start}..{end}?", headers={"Content-Type" : content_type})


# def protein2genomic(protein_id: str, start: int, end: int, ext: str = "/map/translation", content_type: str = 'application/json') -> dict | str:
#     """
#     Protein (AA sequence) to genomic coordinate conversion. For example, start=end=1 returns the chromosome coordinate of the first
#     AA in the protein.
#     """
#     return endpoint_get_base(ext=f"{ext}/{protein_id}/{start}..{end}?", headers={"Content-Type" : content_type})


# def assembly_coordinate_conversions(start: int, end: int, chrm: str, ext: str = "/map/human",
#                                     input_assembly: str = 'GRCh37', output_assembly: str = 'GRCh38', strand: int = 1,
#                                     content_type: str = 'application/json') -> dict | str:
#     """Converts coordinates from input assembly to output assembly."""
#     return endpoint_get_base(ext=f"{ext}/{input_assembly}/{chrm}:{start}..{end}:{strand}/{output_assembly}?", headers={"Content-Type" : content_type})


# def symbol2ENSG_id(symbol: str, species: str = 'homo_sapiens') -> str:
#     """Converts a symbol (e.g. PIK3CA) to ID (e.g. ENSG00000121879)."""
#     return lookup_symbol(symbol, species=species)['id']


# def ENSG_id2symbol(eid: str) -> str:
#     """Converts ID (e.g. ENSG00000121879) to symbol (e.g. PIK3CA)."""
#     return lookup_id(eid)['display_name']


# #def transcript_id2protein_id(trans_id: str) -> str:
# #    """Retrieves the protein ID (ENSP) of a given transcript ID (ENST)."""
# #    return lookup_id(trans_id)['Translation']['id']


# def transcript_id2protein_id_with_version(trans_id: str) -> str:
#     """Retrieves the protein ID (ENSP) with version of a given transcript ID (ENST)."""
#     d = lookup_id(trans_id)['Translation']
#     return f"{d['id']}.{d['version']}"


# def transcript_id2protein_id(trans_id: str) -> str:
#     """Retrieves the protein ID (ENSP) of a given transcript ID (ENST)."""
#     return transcript_id2protein_id_with_version(trans_id).split('.')[0]


# """
# Overlap Information
# ===================
# """
# def region_overlap_info(chrm: str, start: int, end: int, species: str = 'human', features: list = None, content_type: str = 'application/json') -> dict | str:
#     """Retrieves feature information that overlaps with a chromosome region."""
#     if features is None:
#         features = ['gene', 'transcript', 'cds']

#     feature_str = ';'.join([f"feature={x}" for x in features])
#     return endpoint_get_base(ext=f"/overlap/region/{species}/{chrm}:{start}-{end}?{feature_str}", headers={"Content-Type" : content_type})


# def protein_overlap_info(protein_id: str, feature_type: str = None, feature: str = 'protein_feature', content_type: str = 'application/json') -> dict | str:
#     """
#     Retrieves feature information that overlaps with a protein.
#     Use type="Smart" to get the protein domains. Use type=None (or omit type when calling the function) to get all the features.
#     """
#     ext = f"/overlap/translation/{protein_id}?type={feature_type};feature={feature}" if type is not None else f"/overlap/translation/{protein_id}?feature={feature}"
#     return endpoint_get_base(ext=ext, headers={"Content-Type" : content_type})


# """
# Variation endpoint
# ==================
# """
# def variation_endpoint_base(dbSNP: str, species: str = 'human', content_type: str = 'application/json') -> dict | str:
#     """Retrieves the chromosome alleles and position of a given dbSNP rs value (e.g., 'rs77924615va')."""
#     return endpoint_get_base(ext=f"/variation/{species}/{dbSNP}?",
#                              headers={"Content-Type": content_type})


# def variation_variant_consequence(chrm: str, start: int, end: int, var_allele: str, strand: int = 1,
#                                   species: str = 'human', content_type: str = 'application/json') -> dict | str:
#     """
#     Retrieves the consequence of a given variant.

#     For INS, set end = start-1.
#     For DEL, set var_allele to '-'.
#     """
#     return endpoint_get_base(ext=f"/vep/{species}/region/{chrm}:{start}-{end}:{strand}/{var_allele}?",
#                              headers={"Content-Type": content_type})
